import re
from decimal import Decimal
from datetime import datetime
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
import json

from demoritems import DemoRMeta, Review, ReviewLoader

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

import logging

class CurrysSpider(BaseSpider):
    name = 'demo_r-currys.co.uk'
    allowed_domains = ['currys.co.uk', 'reevoo.com']
    user_agent = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:34.0) Gecko/20100101 Firefox/34.0"
    # Ajax call to only show Audio and Computing categories	
    start_urls = ['http://www.currys.co.uk/gb/uk/navbardesktop/sMenuIds/624-642/ajax.html']

    extract_reviews = False

    def parse(self, response):
        data = json.loads(response.body)
        for link in link_generator(data):
            if link:
                yield Request(link, callback=self.parse_categories)

    def parse_categories(self, response):
        
        base_url = get_base_url(response)
        links = response.xpath("//nav[@class = 'section_nav nested ucmsNav']/ul/li/a/@href").extract()
        categories = response.xpath("//nav/ul/li/div/a[@class = 'btn btnBold']/@href").extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_categories)
        for link in links:
            yield Request(urljoin_rfc(base_url, link), callback=self.parse_categories)

        items = response.xpath("//div[contains(@class, 'col12 result')]/article//a/@href").extract()
        try:
            new_page = response.xpath("//a[@class = 'next']/@href").extract()[0]
            yield Request(urljoin_rfc(base_url, new_page), callback=self.parse_categories)
        except:
            pass
        for item in items:
            yield Request(urljoin_rfc(base_url, item), callback=self.parse_items)

    def parse_items(self, response):
        
        description_field = response.xpath("//script[@src = 'http://media.flixfacts.com/js/loader.js']").extract_first()
        if not description_field:
            return
        try:
            name = response.xpath("//span[@itemprop = 'name']/text()").extract()[0].encode('ascii', 'ignore')
        except Exception:
            name = ' '.join(response.xpath("//h1/span/text()").extract()).encode('ascii', 'ignore').strip()

        if not name:
            self.log('Skipping product without name: ' + response.url)
            return

        price = response.xpath("//meta[@property = 'og:price:amount']/@content").extract_first()
        identifier = re.findall(re.compile('data-flix-mpn="(.+?)"'), description_field)[0]
        try:
            sku = response.xpath('//p[@class="prd-code"]/text()').re('Product code: (.*)')[0]
        except:
            sku = ""
        categories = response.xpath("//div[@class = 'breadcrumb']/a/span/text()").extract()[1:4]
        json_data = response.xpath('//script[@type="application/ld+json"]/text()').extract()[-1].strip()
        try:
            data = json.loads(json_data)
            brand = data['brand']['name']
        except Exception:
            brand = ''
        
        stock = response.xpath('//div[@id="content"]//li[@class="available"]')
        stock = 1 if stock else 0
        try:
            image_url = response.xpath("//a/img[@itemprop = 'image']/@src").extract()[0]
        except:
            image_url = response.xpath('//img[@class="product-image"]/@src').extract()
            image_url = image_url[0] if image_url else ""

        l = ProductLoader(item=Product(), response=response)
        l.add_value('image_url', image_url)
        l.add_value('url', response.url)
        l.add_value('name', name)
        l.add_value('price', price)
        l.add_value('stock', stock)

        for category in categories:
            l.add_value('category', category)

        l.add_value('brand', brand)
        l.add_value('sku', sku)
        l.add_value('identifier', identifier)
        product = l.load_item()

        metadata = DemoRMeta()
        metadata['promotion'] = ' '.join(''.join(response.xpath('//div[@id="product-actions"]//strong[@class="offer"]/text()').extract()).split())
        metadata['reviews'] = []
        if price:
            cost_price = Decimal(price) * Decimal('0.9')
            metadata['cost_price'] = cost_price.quantize(Decimal('.01'))
        product['metadata'] = metadata	


        reviews_url = response.xpath('//a[contains(@href, "product_reevo") and contains(@href, "'+identifier+'")]/@href').extract()
        if reviews_url and self.extract_reviews:
            yield Request(reviews_url, callback=self.parse_review_page, meta={'product': product})
        else:
            yield product

    def parse_review_page(self, response):
        item_ = response.meta.get('product', '')
        base_url = get_base_url(response)

        hxs = HtmlXPathSelector(text=json.loads(response.body))
        
        reviews = hxs.select('//article[contains(@id, "review_")]')
        for review in reviews:
            l = ReviewLoader(item=Review(), response=response, date_format='%m/%d/%Y')
            rating = ''.join(review.select('.//div[@class="overall_score_stars"]/@title').extract())
            date = review.select('.//section[@class="purchase_date"]/span/text()').extract()
            if not date:
                date = review.select('.//p[@class="purchase_date"]/span/text()').extract()
            date = date[0].strip() if date else ''
            review_pros = 'Pro: ' + ''.join(review.select('.//section[@class="review-content"]//dd[@class="pros"]//text()').extract()).strip()
            review_cons = 'Cons: ' + ''.join(review.select('.//section[@class="review-content"]//dd[@class="cons"]//text()').extract()).strip()
            review = review_pros + ' ' + review_cons

            l.add_value('rating', rating)
            l.add_value('url', response.url)
            l.add_value('date', datetime.strptime(date, '%d %B %Y').strftime('%m/%d/%Y'))
            l.add_value('full_text', review)
            item_['metadata']['reviews'].append(l.load_item())

        next = hhxs.select('//a[@rel="next"]/text()').extract()

        if next:
            next_url = response.url.split('productReviews')[0]
            next_url = next_url + 'productReviews/iPage/'+next[0]+'/ajax.html'
            yield Request(next_url, callback=self.parse_review_page, meta={'product': item_})
        else:
            yield item_

def link_generator(data):
    '''
    Recursive function to extract category link from nested JSON 
    '''
    for category in data:
        if isinstance(category, list):
             for id_val in link_generator(category):
                   yield id_val
        else:
            for k, v in category.items():
                if k == "link":
                    yield v
                elif isinstance(v, list):
                    for id_val in link_generator(v):
                        yield id_val

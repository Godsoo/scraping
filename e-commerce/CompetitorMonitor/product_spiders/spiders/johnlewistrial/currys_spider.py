import re
from datetime import datetime
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
import json

from johnlewisitems import JohnLewisMeta, Review, ReviewLoader

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

import logging

class CurrysSpider(BaseSpider):
    name = 'johnlewis-trial-currys.co.uk'
    allowed_domains = ['currys.co.uk', 'reevoo.com']
    user_agent = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:34.0) Gecko/20100101 Firefox/34.0"
    start_urls = [
        'http://www.currys.co.uk/gbuk/household-appliances-35-u.html'
    ]

    def start_requests(self):
        yield Request("http://www.currys.co.uk/gbuk/home-appliances/vacuum-cleaners-337-c.html", callback=self.parse_categories)
        yield Request("http://www.currys.co.uk/gb/uk/navbar/iMenuId/2066/ajax.html", callback=self.parse_links)
        yield Request("http://www.currys.co.uk/gbuk/home-appliances/ironing-338-c.html", callback=self.parse_categories)
        yield Request("http://www.currys.co.uk/gb/uk/navbar/iMenuId/2088/ajax.html", callback=self.parse_links)
        yield Request("http://www.currys.co.uk/gbuk/home-appliances/sewing-machines/sewing-machines/470_4135_31889_xx_xx/xx-criteria.html", callback=self.parse_categories)
        yield Request("http://www.currys.co.uk/gb/uk/navbar/iMenuId/5237/ajax.html", callback=self.parse_links)
        yield Request("http://www.currys.co.uk/gbuk/home-appliances/health-beauty-341-c.html", callback=self.parse_categories)
        yield Request("http://www.currys.co.uk/gb/uk/navbar/iMenuId/2765/ajax.html", callback=self.parse_links)
        yield Request("http://www.currys.co.uk/gbuk/household-appliances/small-kitchen-appliances-336-c.html", callback=self.parse_categories)
        yield Request("http://www.currys.co.uk/gb/uk/navbar/iMenuId/2067/ajax.html", callback=self.parse_links)
        yield Request("http://www.currys.co.uk/gbuk/home-appliances/fans-air-conditioning-340-c.html", callback=self.parse_categories)
        yield Request("http://www.currys.co.uk/gb/uk/navbar/iMenuId/2065/ajax.html", callback=self.parse_links)
        yield Request("http://www.currys.co.uk/gbuk/household-appliances/cooking/microwaves/335_3152_32014_xx_xx/xx-criteria.html", callback=self.parse_categories)
        yield Request("http://www.currys.co.uk/gb/uk/navbar/iMenuId/2064/ajax.html", callback=self.parse_links)
        yield Request("http://www.currys.co.uk/gb/uk/navbar/iMenuId/4151/ajax.html", callback=self.parse_links)
        yield Request("http://www.currys.co.uk/gbuk/clearance-household-appliances-1846-commercial.html", callback=self.parse_categories)
        yield Request("http://www.currys.co.uk/gbuk/care-plans-kitchen-appliances-279-commercial.html", callback=self.parse_categories)
        yield Request("http://www.currys.co.uk/gb/uk/navbar/iMenuId/4319/ajax.html", callback=self.parse_links)
        yield Request("http://www.currys.co.uk/gbuk/pc-world-business-1262-commercial.html?intcmp=business-nav-small-appliances", callback=self.parse_categories)

    def parse_links(self, response):
        base_url = get_base_url(response)
        data = json.loads(response.body)
        hxs = HtmlXPathSelector(text=data['content'])
        for url in hxs.select('//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response=response)
        base_url = get_base_url(response)
        links = hxs.select("//nav[@class = 'section_nav nested ucmsNav']/ul/li/a/@href").extract()
        categories = hxs.select("//nav/ul/li/div/a[@class = 'btn btnBold']/@href").extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_categories)
        for link in links:
            yield Request(urljoin_rfc(base_url, link), callback=self.parse_categories)

        items = hxs.select("//div[@class = 'col12 resultList']/article/a/@href").extract()
        try:
            new_page = hxs.select("//a[@class = 'next']/@href").extract()[0]
            yield Request(urljoin_rfc(base_url, new_page), callback=self.parse_categories)
        except:
            pass
        for item in items:
            yield Request(urljoin_rfc(base_url, item), callback=self.parse_items)

    def parse_items(self, response):
        hxs = HtmlXPathSelector(response=response)
        description_field = hxs.select("//script[@src = 'http://media.flixfacts.com/js/loader.js']").extract()[0]
        name = hxs.select("//span[@itemprop = 'name']/text()").extract()[0].encode('ascii', 'ignore')
        price = hxs.select("//meta[@property = 'og:price:amount']/@content").extract()[0]
        identifier = re.findall(re.compile('data-flix-mpn="(.+?)"'), description_field)[0]
        try:
            sku = re.findall(re.compile('data-flix-ean="(\d*)"'), description_field)[0]
        except:
            sku = ""
        categories = hxs.select("//div[@class = 'breadcrumb']/a/span/text()").extract()[1:4]
        brand = hxs.select("//span[@itemprop = 'brand']/text()").extract()[0]
        stock = hxs.select("//section[@class = 'col3']").extract()[0]
        stock = 1 if not re.findall(re.compile('Out of stock'), stock) else 0
        try:
            image_url = hxs.select("//div[@id = 'currentView']//img[@itemprop = 'image']/@src").extract()[0]
        except:
            image_url = ""
        l = ProductLoader(item=Product(), response=response)
        l.add_value('image_url', image_url)
        l.add_value('url', response.url)
        l.add_value('name', name)
        l.add_value('price', price)
        l.add_value('stock', stock)

        for category in categories:
            l.add_value('category', categories)

        l.add_value('brand', brand)
        l.add_value('sku', sku)
        l.add_value('identifier', identifier)
        product = l.load_item()

        metadata = JohnLewisMeta()
        metadata['promotion'] = ''.join(hxs.select('normalize-space(//span[@class="offerSaving"]/text())').extract())
        metadata['reviews'] = []
        product['metadata'] = metadata


        reviews_url = hxs.select('//a[@class="reevoomark"]/@href').extract()[0]
        
        yield Request(reviews_url, callback=self.parse_review_page, meta={'product': product})

    def parse_review_page(self, response):
        item_ = response.meta.get('product', '')
        base_url = get_base_url(response)

        hxs = HtmlXPathSelector(response=response)
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

        next = hxs.select('//a[@class="next_page"]/@href').extract()

        if next:
            yield Request(urljoin_rfc(base_url, next[0]), callback=self.parse_review_page, meta={'product': item_})
        else:
            yield item_

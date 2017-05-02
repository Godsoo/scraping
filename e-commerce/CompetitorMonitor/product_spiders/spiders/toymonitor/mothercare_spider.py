import os
import re
import xlrd
import paramiko

from datetime import datetime

from scrapy import log

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from w3lib.url import url_query_cleaner

from utils import brand_in_file

from toymonitoritems import ToyMonitorMeta, Review, ReviewLoader

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from brands import BrandSelector

HERE = os.path.abspath(os.path.dirname(__file__))

class MothercareSpider(BaseSpider):
    name = 'toymonitor-mothercare.com'
    allowed_domains = ['mothercare.com', 'mark.reevoo.com']
    start_urls = ['http://www.mothercare.com/toys/cat_toys,default,sc.html']
    errors = []
    brand_selector = BrandSelector(errors)
    #field_modifiers = {'brand': brand_selector.get_brand}

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = response.xpath('//ul[@id="category-level-1"]//a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))

        products = response.css('div.b-product_title a::attr(href)').extract()
        for product in products:
            yield Request(url_query_cleaner(response.urljoin(product)), 
                          callback=self.parse_product, 
                          meta=response.meta)

        pages = response.css('ul.b-pagination a::attr(href)').extract()
        for url in pages:
            yield Request(url, meta=response.meta)

        identifier = hxs.select('//p[contains(@class, "productid")]/@class').re('p_(.*)')
        if identifier:
            yield Request(response.url, dont_filter=True, callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//input[@id="product-name"]/@value')
        loader.add_value('url', response.url)
        loader.add_css('brand', 'span.b-brand_title::text')
        categories = response.css('div.b-breadcrumbs a::text').extract()[2:]
        loader.add_value('category', categories)

        loader.add_xpath('sku', '//meta[@itemprop="model"]/@content')
        identifier = response.xpath('//input[@name="pid"]/@value').extract()
        if not identifier:
            log.msg('PRODUCT WHIOUT IDENTIFIER: ' + response.url)
            return

        loader.add_value('identifier', identifier[0])
        image_url = response.xpath('//link[@rel="image_src"]/@href').extract() or response.xpath('//meta[@itemprop="image"]/@content').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])

        price = response.xpath('//meta[@itemprop="price"]/@content').extract()
        loader.add_value('price', price)

        out_of_stock = response.css('div.b-availability').xpath('.//span[@data-availability="NOT_AVAILABLE"]')
        if out_of_stock:
            loader.add_value('stock', '0')

        product = loader.load_item()

        promo = response.xpath('//div[@class="b-product_promo"]/div/span/text()').extract()

        metadata = ToyMonitorMeta()
        metadata['reviews'] = []
        if promo:
            metadata['promotions'] = promo[0].strip()
        product['metadata'] = metadata

        reviews_url = 'http://mark.reevoo.com/reevoomark/en-GB/product.html?page=1&sku=%s&tab=reviews&trkref=MOT'

        yield Request(reviews_url % identifier[0], callback=self.parse_review_page, meta={'product': product})

    def parse_review_page(self, response):
        item_ = response.meta.get('product', '')
        base_url = get_base_url(response)

        rating_mapping = {'1': '1', '2': '1', '3': '2', '4': '2', '5': '3', 
                          '6': '3', '7': '4', '8': '4', '9': '5', '10': '5'}

        reviews = response.xpath('//article[contains(@id, "review_")]')
        for review in reviews:
            l = ReviewLoader(item=Review(), response=response, date_format='%d/%m/%Y')
            rating = ''.join(review.xpath('.//div[@class="overall_score_stars"]/@title').extract())
            date = review.xpath('.//section[@class="purchase_date"]/span/text()').extract()
            if not date:
                date = review.xpath('.//p[@class="purchase_date"]/span/text()').extract()
            date = date[0].strip() if date else ''
            review_pros = 'Pro: ' + ''.join(review.xpath('.//section[@class="review-content"]//dd[@class="pros"]//text()').extract()).strip()
            review_cons = 'Cons: ' + ''.join(review.xpath('.//section[@class="review-content"]//dd[@class="cons"]//text()').extract()).strip()
            review = review_pros + ' ' + review_cons

            l.add_value('rating', rating_mapping[rating])
            l.add_value('url', response.url)
            l.add_value('date', datetime.strptime(date, '%d %B %Y').strftime('%d/%m/%Y'))
            l.add_value('full_text', review)
            item_['metadata']['reviews'].append(l.load_item())

        next = response.xpath('//a[@class="next_page"]/@href').extract()

        if next:
            yield Request(urljoin_rfc(base_url, next[0]), callback=self.parse_review_page, meta={'product': item_})
        else:
            yield item_


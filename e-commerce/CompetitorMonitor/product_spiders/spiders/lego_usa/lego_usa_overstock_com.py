import csv
import os
import json
import copy
import re

from scrapy.spider import BaseSpider
from scrapy import Selector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, url_query_parameter, add_or_replace_parameter
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy.shell import inspect_response

HERE = os.path.abspath(os.path.dirname(__file__))


class OverstockSpider(BaseSpider):
    name = 'lego_usa_overstock_com'
    allowed_domains = ['overstock.com']
    rotate_agent = True
    start_urls = ('http://www.overstock.com/LEGO,/brand,/results.html?sort=Recommended&TID=SORT:Recommended&count=250&infinite=true',)

    def start_requests(self):
        yield FormRequest('http://www.overstock.com/intlcountryselect',
                          formdata={'country': 'US'},
                          callback=self.parse_shipping)

    def parse_shipping(self, response):
        yield Request('http://www.overstock.com/LEGO,/brand,/results.html?sort=Recommended&TID=SORT:Recommended&count=250&infinite=true', meta={'index': 0})

    def parse(self, response):
        data = json.loads(response.body)
        if data['hasMore']:
            index = response.meta.get('index', 0) + 150
            url = add_or_replace_parameter(self.start_urls[0], 'index', str(index))
            yield Request(url, meta={'index': index})
            self.log('NEXT PAGE')
        sel = Selector(text=data['html'])
        base_url = get_base_url(response)

        for url in sel.xpath('//a[@class="pro-thumb"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        for product in data['request']['products']:
            yield Request(product['urls']['productPage'], callback=self.parse_product)
        

    def parse_product(self, response):

        sel = Selector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), selector=sel)
        loader.add_xpath('identifier', '//input[@name="productQuestionProductId"]/@value')
        loader.add_xpath('name', '//div[@itemprop="name"]//h1/text()')
        loader.add_value('brand', 'Lego')
        loader.add_xpath('sku', '//td[@itemprop="mpn"]/text()')
        loader.add_value('url', response.url)
        loader.add_xpath('price', '//*[@id="cat-prod-det-reg-price"]/text()//*[@id="mainCenter_priceDescWrap"]//span[@itemprop="price"]|//div[@id="pricing-container"]//span[@itemprop="price"]/text()')
        #if not loader.get_output_value('price'):
            #return
        image_url = sel.xpath('//img[@itemprop="image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

        for category in sel.xpath('//ul[@class="breadcrumbs"]/li/a/span/text()').extract():
            loader.add_value('category', category)
        yield loader.load_item()

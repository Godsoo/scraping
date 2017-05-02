import re
import os
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse, TextResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
import hashlib
from decimal import Decimal

import csv

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class ArcEuroTradeSpider(BaseSpider):
    name = 'arceurotrade.co.uk'
    allowed_domains = ['arceurotrade.co.uk', 'www.arceurotrade.co.uk']
    start_urls = (u'http://www.arceurotrade.co.uk/quick-index.aspx', )

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        categories = hxs.select(u'//li[@class="QuickIndexLink"]/a/@href').extract()
        categories += hxs.select(u'//div[@class="DepartmentName"]/a/@href').extract()
        categories += hxs.select(u'//dl[@id="Navigation"]//a/@href').extract()
        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url)

        for product in self.parse_product(response):
            yield product

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        products = hxs.select(u'//table[@id="ProdTable"]//tr')
        for product in products:
            name = product.select(u'./td[2]/text()')[0].extract().split()
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_value('url', response.url)
            loader.add_value('name', name)
            price = product.select(u'./td[3]/text()')[0].extract().strip()
            price = price[1:] if price[0] == u'\xa3' else price
            price = round(float(price) / 1.2, 2)
            loader.add_value('price', price)
            # if loader.get_output_value('price'):
            yield loader.load_item()

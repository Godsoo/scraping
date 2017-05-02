# -*- coding: utf-8 -*-
import csv
import json
import os
import shutil
from datetime import datetime
import StringIO
import urlparse
import re
import hashlib
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import CloseSpider
from scrapy import signals

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader, ProductLoaderEU
from product_spiders.utils import extract_price_eu, extract_price


HERE = os.path.abspath(os.path.dirname(__file__))


class MobilestationSpider(BaseSpider):
    name = 'mobilestation.co.nz'
    allowed_domains = ['mobilestation.co.nz']
    start_urls = ['http://www.mobilestation.co.nz']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        # we extract the categories urls
        categories = hxs.select('//ul[@class="mainnav"]/li//a/@href').extract()
        for category in categories:
            yield Request(
                category,
                callback=self.parse_category
            )

    def parse_category(self, response):
        """
        While parsing a category page we need to look after a product or category list
        """
        hxs = HtmlXPathSelector(response)
        # products
        for product_url in hxs.select('//ul[contains(@class, "products-grid")]/li//div[@class="item-title"]/a/@href').extract():
            yield Request(product_url, callback=self.parse_product)

        # next page
        next_page_url_list = hxs.select('//div[@class="pages"]/ol/li/a/@href').extract()
        for url in next_page_url_list:
            yield Request(url, callback=self.parse_category)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('price', '//span[@class="price"]/text()')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@class="product-name"]/text()')
        if hxs.select('//p[contains(@class, "in-stock")]'):
            stock = '1'
        else:
            stock = '0'
        loader.add_value('stock', stock)
        categories = hxs.select('//ul[@class="breadcrumbs"]/li/a/text()').extract()[1:]
        loader.add_value('category', categories)
        loader.add_value('brand', "")

        category = ''.join(categories)
        if [x for x in ['memory card', 'accessories'] if x in category.lower()]:
            shipping = '0'
        else:
            shipping = '30'
        loader.add_value('shipping_cost', shipping)
        sku = hxs.select('//input[@name="product"]/@value').extract()[0].strip()
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)
        loader.add_xpath('image_url', '//img[@id="image"]/@src')
        yield loader.load_item()
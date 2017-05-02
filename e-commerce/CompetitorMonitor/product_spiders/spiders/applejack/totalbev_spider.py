# -*- coding: utf-8 -*-

import re
import os
import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
import hashlib

from product_spiders.utils import extract_price

import csv

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class TotalBevSpider(BaseSpider):
    name = 'applejack-totalbev.com'
    allowed_domains = ['totalbev.com']
    start_urls = ('http://totalbev.com/',)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        # categories
        categories = hxs.select('//div[@class="line1"]//a/@href').extract()
        categories += hxs.select('//div[@id="category"]//li/a/@href').extract()
        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url)

        # products
        products = hxs.select('//a[@class="product-title"]/@href').extract()
        for url in products:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product)

        # pagination
        next_page = hxs.select('//div[@class="nav-pages"]/a[@class="right-arrow"]/@href').extract()
        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(next_page)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(selector=hxs, item=Product())
        loader.add_value('url', response.url)
        name = hxs.select('//h1/text()').extract()[0].strip()
        product_size = hxs.select('//tr[td[contains(text(), "Size")]]/td[@class="property-value"]/text()').extract()
        if product_size:
            name += u' ' + product_size[-1].strip()

        price = hxs.select('//span[@id="product_price"]/text()').extract()[0]

        loader.add_value('name', name)
        loader.add_value('price', price)

        categories = hxs.select('//a[@class="bread-crumb"]/text()').extract()[1:]
        loader.add_value('category', categories)

        loader.add_value('brand', '')

        image_url = hxs.select('//img[@id="product_thumbnail"]/@src').extract()
        loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[-1]))

        identifier = hxs.select('//input[@name="productid"]/@value').extract()
        loader.add_value('identifier', identifier[0])
        loader.add_value('sku', identifier[0])
        yield loader.load_item()

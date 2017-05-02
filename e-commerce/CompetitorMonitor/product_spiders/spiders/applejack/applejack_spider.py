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


class ApplejackSpider(BaseSpider):
    name = 'applejack-applejack.com'
    allowed_domains = ['applejack.com']
    start_urls = ('https://www.applejack.com',)

    def start_requests(self):
        with open(os.path.join(HERE, 'applejack_skus.csv'), 'rb') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row['Item'].zfill(5)
                search_url = "https://www.applejack.com/websearch_results.html?kw=" + sku
                yield Request(search_url, meta={'sku': sku, 'category': row['Category']})

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//div[@class="product-list"]//td/a[@class="rebl15"]/@href').extract()
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, meta=response.meta)

        identifier = hxs.select('//td[@itemprop="sku"]/text()').extract()
        if identifier:
            for item in self.parse_product(response):
                yield item 

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        identifier = hxs.select('//td[@itemprop="sku"]/text()')[0].extract()
        if identifier.strip().upper() != response.meta['sku'].strip().upper():
            log.msg('Wrong product, product SKU: %s, search SKU: %s ' % (identifier, response.meta['sku']))
            return

        loader = ProductLoader(selector=hxs, item=Product())
        identifier = hxs.select('//input[@name="wp"]/@value').extract()
        if not identifier:
            identifier = response.url.split('-')[-1]
        loader.add_value('identifier', identifier)
        loader.add_value('sku', response.meta['sku'])
        loader.add_value('category', response.meta['category'])
        loader.add_value('url', response.url)

        name = hxs.select('//span[@itemprop="name"]/h1/text()').extract()[0].strip()
        loader.add_value('name', name)

        price =  hxs.select('//h2[@itemprop="price"]/text()').extract()
        if not price:
            price =  hxs.select('//span[@itemprop="price"]/text()').extract()
        price = price[0] if price else '0'
        loader.add_value('price', price)
       
        #categories = hxs.select('//a[@class="bread-crumb"]/text()').extract()[1:]
        #loader.add_value('category', categories)

        brand = hxs.select('//a[@class="prodlink"]/span/text()').extract()
        brand = brand[0] if brand else ''
        loader.add_value('brand', brand)

        image_url = hxs.select('//div[@class="prod_detail"]/div[@id="imghid"]/img/@src').extract()
        if not image_url:
            image_url = hxs.select('//div[@class="contentdiv"]//img[@class="thumbs"]/@src').extract()
        loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[-1]))

        yield loader.load_item()

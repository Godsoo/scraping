import re
import json
import os
import csv
import paramiko

import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.item import Item, Field

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class WexMeta(Item):
    condition = Field()


class mpbSpider(BaseSpider):
    name = 'wexphotographic-mpb.co'
    allowed_domains = ['mpb.com']

    start_urls = ['https://www.mpb.com/en-uk/used-equipment']

    def parse(self, response):
        base_url = get_base_url(response)

        products = response.xpath('//header[@class="theme-tile-header"]//a/@href').extract()
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, callback=self.parse_products)

        next = response.xpath('//div[contains(@class, "next-results")]/@data-next-results-url').extract()
        if next:
            url = urljoin_rfc(base_url, next[0])
            yield Request(url)

    def parse_products(self, response):
        base_url = get_base_url(response)

        products = response.xpath('//div[contains(@class, "product-list")]//a[contains(@class, "product-link")]/@href').extract()
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
 

        loader = ProductLoader(response=response, item=Product())
        loader.add_xpath('identifier', '//span[@class="www-product-sku"]/text()')
        loader.add_value('sku', '')
        categories = response.xpath('//ol[contains(@class, "breadcrumb")]/li/a/text()').extract()[3:-2]
        loader.add_value('brand', '')
        loader.add_value('category', categories)
        loader.add_xpath('name', '//h1[contains(@class, "product-name")]/text()')
        price = response.xpath('//b[contains(@class, "product-price")]/text()').extract()
        if price:
            price = price[0]
        else:
            self.log('NO PRICE!!!')
            return
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        image_url = urljoin_rfc(get_base_url(response), image_url[0].strip()) if image_url else ''
        loader.add_value('image_url', image_url)

        condition = response.xpath('//span[@class="theme-accent www-product-condition"]/text()').extract()
        metadata = WexMeta()
        metadata['condition'] = condition[0].strip() if condition else ''

        product = loader.load_item()
        product['metadata'] = metadata
        yield product

# -*- coding: utf-8 -*-

"""
Arris International account
Client spider
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5551
"""

import os
import csv
from scrapy.spider import BaseSpider
from scrapy.http import Request


from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class SurfboardeSpider(BaseSpider):
    name = 'arris_international-surfboard.com'

    filename = os.path.join(HERE, 'arris_international_products.csv')
    start_urls = ('file://' + filename,)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['SKU'])
            loader.add_value('sku', row['SKU'])
            loader.add_value('brand', 'SurfBoard')
            loader.add_value('url', row['URL'])
            loader.add_value('category', row['Category'].decode('utf8'))
            loader.add_value('name', row['Product Name '].decode('utf8'))
            loader.add_value('price', 0)
            item = loader.load_item()
            yield Request(row['URL'], callback=self.parse_product, meta={'item': item})

    def parse_product(self, response):
        item = response.meta['item']
        price = response.xpath('//*[@itemprop="price"]/@content').extract()
        item['price'] = extract_price(price[0])
        yield item

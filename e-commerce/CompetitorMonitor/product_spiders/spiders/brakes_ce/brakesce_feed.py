# -*- coding: utf-8 -*-
"""
This spider is set to extract items from a feed provided by the customer, the prices are extracted from the product pages.
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/4842-brakes-ce-|-client-spider/details#
"""

import os
import csv
from StringIO import StringIO

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.item import Item, Field

from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))


class BrakesCEMeta(Item):
    mpn = Field()


class BrakesCESpider(BaseSpider):
    name = 'brakes_ce-feed'
    filename = os.path.join(HERE, 'brakesce_products.csv')
    start_urls = ('file://' + filename,)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['Brakes Code'].lower())
            loader.add_value('sku', row['Brakes Code'].lower())
            loader.add_value('brand', row['Brand/Category'])
            loader.add_value('category', row['Brand/Category'])
            loader.add_value('image_url', row['Image URL'])
            loader.add_value('name', row['Product Name'].decode('utf8'))
            loader.add_value('url', row['Product Page URL'])
            item = loader.load_item()
            metadata = BrakesCEMeta()
            metadata['mpn'] = row['Unique Manufacturers Product Code']
            item['metadata'] = metadata
            yield Request(row['Product Page URL'],
                          meta={'item': item},
                          callback=self.parse_price)

    def parse_price(self, response):
        price = response.xpath('//div[@id="prodPurchase"]//div[@class="exVatPanel"]'
                               '//span[@itemprop="price"]/text()').extract()
        item = response.meta.get('item')
        item['price'] = extract_price(price[0]) if price else '0.00'
        yield item

# -*- coding: utf-8 -*-

"""
Bush Industries trial account
Client spider
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5552
"""

import os
import csv
from scrapy.spider import BaseSpider

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

from bushindustriesitems import BushIndustriesMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class BushFurnitureSpider(BaseSpider):
    name = 'bushindustries-bushfurniture.com'

    filename = os.path.join(HERE, 'bush_industries_flat_file.csv')
    start_urls = ('file://' + filename,)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['UPC'])
            loader.add_value('sku', row['UPC'])
            loader.add_value('brand', row['BRAND NAME'].decode('utf8'))
            loader.add_value('category', row['CATEGORY NAME'].decode('utf8'))
            loader.add_value('name', row['PRODUCT NAME'].decode('utf8'))
            loader.add_value('price', row['Price'])
            loader.add_value('image_url', row['Product Image URL'])
            loader.add_value('url', row['Retailer URL'])

            item = loader.load_item()

            metadata = BushIndustriesMeta()
            metadata['mpn'] = row['MPN']
            metadata['asin'] = row['ASIN']
            item['metadata'] = metadata

            yield item


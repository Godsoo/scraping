# -*- coding: latin-1 -*-

import os
import csv
from scrapy.item import Item, Field
from scrapy.spider import BaseSpider

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class WexMeta(Item):
    condition = Field()
    mpn = Field()
    model_number = Field()


class WexSpider(BaseSpider):
    name = 'wexphotographic_new-wexphotographic.com'

    start_urls = ('http://www.wexphotographic.com/webcontent/productfeed/googlebase/gbproducts.txt',)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body), delimiter="|")
        for row in reader:
            if row['condition'] != 'new':
                continue
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['id'].lower())
            loader.add_value('sku', row['id'])
            loader.add_value('brand', row['brand'])
            loader.add_value('url', row['link'].decode('latin-1'))
            loader.add_value('image_url', row['image_link'])
            categories = row['product_type'].split(' > ') if row.get('product_type', '') else ''
            for category in categories:
                loader.add_value('category', category)

            name = row.get('title', '')
            if not name:
                log.msg('ERROR >>> Product without name, ID: ' + row['id'])
                continue
            if row.get('color', ''):
                color = row.get('color', '')
                if color.upper().strip() != 'N/A':
                    name = name + ' ' + color
            loader.add_value('name', name.decode('latin-1'))
            loader.add_value('price', row['price'])
            loader.add_value('shipping_cost', row['shipping'])
            if row['availability'] == 'preorder':
                loader.add_value('stock', 0)
            product = loader.load_item()

            metadata = WexMeta()
            metadata['condition'] = row['condition']
            metadata['mpn'] = row['mpn']
            metadata['model_number'] = row['model_number']

            product['metadata'] = metadata
            yield product

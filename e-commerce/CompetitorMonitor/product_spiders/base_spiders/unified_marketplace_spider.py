# -*- coding: utf-8 -*-
import csv
import json
import os

try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/unified_marketplace'))


class UnifiedMarketplaceSpider(BaseSpider):
    # To be set as 'direct' or 'marketplace'
    market_type = 'direct'
    data_filename = ''

    def __init__(self, *args, **kwargs):
        super(UnifiedMarketplaceSpider, self).__init__(*args, **kwargs)

    def _load_item(self, product, response):
        loader = ProductLoader(Product(), response=response)
        loader.add_value('identifier', product['identifier'])
        loader.add_value('name', product['name'])
        loader.add_value('url', product['url'])
        loader.add_value('price', product['price'])
        loader.add_value('sku', product['sku'])
        if 'stock' in product and product['stock']:
            loader.add_value('stock', product['stock'])
        if 'image_url' in product and product['image_url']:
            loader.add_value('image_url', product['image_url'])
        if 'brand' in product and product['brand']:
            loader.add_value('brand', product['brand'])
        if 'category' in product and product['category']:
            loader.add_value('category', product['category'])
        if 'dealer' in product and product['dealer']:
            loader.add_value('dealer', product['dealer'])
        if 'shipping_cost' in product and product['shipping_cost']:
            loader.add_value('shipping_cost', product['shipping_cost'])

        item = loader.load_item()
        if 'metadata' in product and product['metadata']:
            item['metadata'] = product['metadata']
        return item

    def parse(self, response):
        if self.market_type == 'marketplace' and self.data_filename:
            meta = {}
            meta_name = os.path.join(DATA_DIR, self.data_filename + '.json-lines')
            if os.path.exists(meta_name):
                f1 = open(meta_name)
                for line in f1:
                    product = json.loads(line)
                    meta[product['identifier']] = product['metadata']

            f = open(os.path.join(DATA_DIR, self.data_filename + '.csv'))
            for row in csv.DictReader(f):
                product = {}
                for key, value in row.items():
                    product[key] = value.decode('utf-8')

                if not product:
                    continue

                if product['identifier'] in meta:
                    product['metadata'] = meta[product['identifier']]

                yield self._load_item(product, response)

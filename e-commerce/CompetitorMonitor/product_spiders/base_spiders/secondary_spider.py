# -*- coding: utf-8 -*-
import os.path
import csv
import json

try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider

from product_spiders.items import Product, ProductLoader
from cStringIO import StringIO
from scrapy.exceptions import CloseSpider


HERE = os.path.abspath(os.path.dirname(__file__))
PRODUCT_SPIDERS_FOLDER = os.path.dirname(HERE)
SPIDERS_FOLDER = os.path.join(PRODUCT_SPIDERS_FOLDER, 'spiders')


class SecondaryBaseSpider(BaseSpider):
    """
    Base class for spiders using other spider's crawl results

    Mandatory attributes:
    'csv_file' - path to csv file with previous crawls results, using 'product_spiders/spiders/ folder as root
    """

    # default product loader, allows using custom product loader
    product_loader = ProductLoader

    csv_file = None
    is_absolute_path = False

    errors = []

    def __init__(self, *args, **kwargs):
        super(SecondaryBaseSpider, self).__init__(*args, **kwargs)

        products_file = ''
        error_msg = ''
        if hasattr(self, 'json_file') and self.json_file:
            if not self.is_absolute_path:
                products_file = os.path.join(SPIDERS_FOLDER, self.json_file)
            else:
                products_file = self.json_file
        else:
            if not hasattr(self, 'csv_file') or self.csv_file is None:
                error_msg = "Secondary Spider issue: spider has no attribute 'csv_file' or 'json_file'"
                self.errors.append(error_msg)
            else:
                if not self.is_absolute_path:
                    products_file = os.path.join(SPIDERS_FOLDER, self.csv_file)
                else:
                    products_file = self.csv_file

        if not products_file:
            raise CloseSpider(reason=error_msg)

        self.start_urls = ['file://' + products_file]

    def preprocess_product(self, item):
        """
        Use this function if you want to preprocess items somehow:
        - Transform any field
        - Give value to field based on values of other fields
        - Filter out some products (return None if you want to filter it out, otherwise return item)
        :param item:
        :return:
        """
        return item

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
        if hasattr(self, 'json_file') and self.json_file:
            for row in StringIO(response.body):
                product = json.loads(row)
                product = self.preprocess_product(product)
                print product
                if not product:
                    continue
                yield self._load_item(product, response)
        else:
            for row in csv.DictReader(StringIO(response.body)):
                product = {}
                for key, value in row.items():
                    product[key] = value.decode('utf-8')

                product = self.preprocess_product(product)
                if not product:
                    continue
                yield self._load_item(product, response)

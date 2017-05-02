import os
import csv
from scrapy.spider import BaseSpider

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

from product_spiders.utils import extract_price_eu as extract_price


HERE = os.path.abspath(os.path.dirname(__file__))


class AquacadabraSpider(BaseSpider):
    name = 'aquacadabra-aquacadabra.com'

    filename = os.path.join(HERE, 'aquacadabra_products.csv')
    start_urls = ('file://' + filename,)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['ID'].lower())
            loader.add_value('sku', row['ID'])
            loader.add_value('brand', '')
            loader.add_value('category', '')
            loader.add_value('name', row['Name'].decode('utf8'))
            loader.add_value('price', extract_price(row['Price']))
            yield loader.load_item()

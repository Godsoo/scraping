import os
import csv
from scrapy.spider import BaseSpider

from utils import extract_price_eu as extract_price
from product_spiders.items import Product

from hamiltonitems import ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class LegoFranceSpider(BaseSpider):
    name = 'hamiltonbeach.com'
    allowed_domains = ['hamiltonbeach.com']
    start_urls = ('http://www.hamiltonbeach.com',)

    def parse(self, response):

        skus = []


        with open(os.path.join(HERE, 'hamiltonbeach_skus.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row['sku'] and not row['identifier'] or 'AEROGARDEN' in row['name'].upper():
                    continue

                loader = ProductLoader(response=response, item=Product())
                sku = unicode(row['sku'], 'iso-8859-1', errors='replace')
                identifier = unicode(row['identifier'], 'iso-8859-1', errors='replace')
                loader.add_value('identifier', identifier)
                loader.add_value('sku', sku)
                loader.add_value('brand', row['brand'])
                name = row['name']
                if not name:
                    name = row['sku']
                loader.add_value('name', unicode(name, 'iso-8859-1', errors='replace'))
                loader.add_value('category', row['category'])
                loader.add_value('price', 0)
                yield loader.load_item()

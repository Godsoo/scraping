import os
import csv
from scrapy.spider import BaseSpider

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class LegoBelgiumSpider(BaseSpider):
    name = 'legobe-lego.com'

    lego_filename = os.path.join(HERE, 'legobe_products.csv')
    start_urls = ('file://' + lego_filename,)

    def __init__(self, *args, **kwargs):
        super(LegoBelgiumSpider, self).__init__(*args, **kwargs)
        self.seen_ids = set()

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['Product No.'].lower())
            loader.add_value('sku', row['Product No.'])
            loader.add_value('brand', 'LEGO')
            loader.add_value('category', row['Theme'].decode('utf8'))
            loader.add_value('name', row['Item Description Local (Dutch)'].decode('utf8'))
            loader.add_value('price', row['RRP Price EUR'])
            if row['Product No.'].lower() not in self.seen_ids:
                self.seen_ids.add(row['Product No.'].lower())
                yield loader.load_item()

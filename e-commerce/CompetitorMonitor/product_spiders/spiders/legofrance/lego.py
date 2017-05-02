import os
import csv
from scrapy.spider import BaseSpider

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class LegoFranceSpider(BaseSpider):
    name = 'lego-france.com'

    lego_filename = os.path.join(HERE, 'lego.csv')
    start_urls = ('file://' + lego_filename,)

    def __init__(self, *args, **kwargs):
        super(LegoFranceSpider, self).__init__(*args, **kwargs)
        self.seen_ids = set()

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['sku'].lower())
            loader.add_value('sku', row['sku'])
            loader.add_value('brand', 'LEGO')
            loader.add_value('category', row['category'].decode('utf8'))
            loader.add_value('name', row['name'].decode('utf8'))
            loader.add_value('price', row['price'])
            if row['sku'].lower() not in self.seen_ids:
                self.seen_ids.add(row['sku'].lower())
                yield loader.load_item()

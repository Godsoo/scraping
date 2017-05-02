import os
import csv
from scrapy.spider import BaseSpider

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))

class LegoNlSpider(BaseSpider):
    name = 'lego-nl.com'

    lego_filename = os.path.join(HERE, 'legonl_products.csv')
    start_urls = ('file://' + lego_filename,)

    def __init__(self, *args, **kwargs):
        super(LegoNlSpider, self).__init__(*args, **kwargs)
        self.seen_ids = set()


    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            if row['Item no'] and row['Item Description English']:
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('sku', row['Product No.'])
                loader.add_value('brand', 'LEGO')
                loader.add_value('category', unicode(row['Theme'].decode('utf-8')))
                loader.add_value('name', unicode(row['Item Description English'].decode('utf-8')))
                loader.add_value('price', row.get('RRP price EUR'))
                loader.add_value('identifier', row['Item no'].lower())
                if row['Item no'].lower() not in self.seen_ids:
                    self.seen_ids.add(row['Item no'].lower())
                    yield loader.load_item()

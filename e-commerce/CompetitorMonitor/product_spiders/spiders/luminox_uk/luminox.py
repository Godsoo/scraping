import os
import csv
from scrapy.spider import BaseSpider

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class LuminoxSpider(BaseSpider):
    name = 'luminox_uk-luminox.com'

    filename = os.path.join(HERE, 'luminox.csv')
    start_urls = ('file://' + filename,)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['Luminox Rerence'].lower())
            loader.add_value('sku', row['Luminox Rerence'])
            loader.add_value('brand', row['Brand'])
            loader.add_value('image_url', 'http://' + row['Image'])
            loader.add_value('name', row['Series name'].decode('utf8'))
            loader.add_value('price', row['SRP in POUNDS'])
            yield loader.load_item()

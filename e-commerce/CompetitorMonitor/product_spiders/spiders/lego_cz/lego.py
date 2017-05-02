import os
import csv
from scrapy.spider import BaseSpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class LegoCZSpider(BaseSpider):
    name = 'legocz-lego.com'

    lego_filename = os.path.join(HERE, 'lego.csv')
    start_urls = ('file://' + lego_filename,)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['Product Code'].lower())
            loader.add_value('sku', row['Product Code'])
            loader.add_value('category', unicode(row['Category'].decode('utf-8')))
            loader.add_value('name', unicode(row['Product Name'].decode('utf-8')))
            loader.add_value('price', row['Price'])
            yield loader.load_item()

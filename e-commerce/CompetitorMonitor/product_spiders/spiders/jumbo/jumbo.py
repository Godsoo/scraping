import os
import csv
from scrapy.spider import BaseSpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class JumboSpider(BaseSpider):
    name = 'jumbo.com'

    data_filename = os.path.join(HERE, 'jumbodata.csv')
    start_urls = ('file://' + data_filename,)

    def parse(self, response):
        reader = csv.reader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row[0])
            loader.add_value('sku', row[0])
            loader.add_value('category', row[9].decode('utf-8'))
            loader.add_value('name', row[3].decode('utf-8'))
            loader.add_value('price', row[11].replace(',', '.'))
            yield loader.load_item()
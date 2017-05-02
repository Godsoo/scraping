import os
import csv
from scrapy.spider import BaseSpider

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class HealthSpanSpider(BaseSpider):
    name = 'healthspan-healthspan.co.uk'

    filename = os.path.join(HERE, 'healthspantrial.csv')
    start_urls = ('file://' + filename,)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['identifier'])
            loader.add_value('url', row['URL'])
            loader.add_value('name', row['Product Name'] + ' ' + row['Pack size'])
            loader.add_value('price', extract_price(row['Price']))
            yield loader.load_item()

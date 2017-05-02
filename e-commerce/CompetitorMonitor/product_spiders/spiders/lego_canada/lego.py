import os
import csv
from scrapy.spider import BaseSpider

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

from legocanadaitems import LegoCanadaMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class LegoFranceSpider(BaseSpider):
    name = 'lego-canada.com'

    lego_filename = os.path.join(HERE, 'legocanada_products.csv')
    start_urls = ('file://' + lego_filename,)

    def __init__(self, *args, **kwargs):
        super(LegoFranceSpider, self).__init__(*args, **kwargs)
        self.seen_ids = set()

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['Product Number'].lower())
            loader.add_value('sku', row['Product Number'])
            loader.add_value('brand', 'LEGO')
            loader.add_value('category', row['Theme'].decode('utf8'))
            loader.add_value('name', row['Product Description'].decode('utf8'))
            loader.add_value('price', row['RRP'])
            item = loader.load_item()
            metadata = LegoCanadaMeta()
            metadata['on_shelf'] = row['On Shelf']
            metadata['launch_date'] = row['Launch Date']
            metadata['exit_date'] = row['Exit Date']
            metadata['margin'] = row['Margin']
            item['metadata'] = metadata
            if row['Product Number'].lower() not in self.seen_ids:
                self.seen_ids.add(row['Product Number'].lower())
                yield item

import os
import csv

from scrapy.spider import BaseSpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class LegoUsaSpider(BaseSpider):
    name = 'lego-usa.com'

    lego_filename = os.path.join(HERE, 'lego.csv')
    start_urls = ('file://' + lego_filename,)

    def __init__(self, *args, **kwargs):
        super(LegoUsaSpider, self).__init__(*args, **kwargs)
        self.seen_ids = set()

    def parse(self, response):
        reader = csv.reader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row[2].lower())
            loader.add_value('sku', row[2])
            loader.add_value('category', row[1].decode('utf8'))
            loader.add_value('name', row[3].decode('utf8'))
            loader.add_value('price', row[4])

            item = loader.load_item()
            item['metadata'] = {
                'Launch Date': row[5],
                'Exit Date': row[6],
                'Margin': row[7],
            }

            if item['identifier'] not in self.seen_ids:
                self.seen_ids.add(item['identifier'])
                yield item

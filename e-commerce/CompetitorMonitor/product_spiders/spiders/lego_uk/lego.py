import os
import csv
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class LegoUKSpider(BaseSpider):
    name = 'legouk-lego.com'

    lego_filename = os.path.join(HERE, 'lego.csv')
    start_urls = ('file://' + lego_filename,)

    def __init__(self, *args, **kwargs):
        super(LegoUKSpider, self).__init__(*args, **kwargs)
        self.seen_ids = set()

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['sku'].lower())
            loader.add_value('sku', row['sku'])
            loader.add_value('category', row['category'])
            loader.add_value('name', row['name'].decode('utf', errors="ignore"))
            loader.add_value('price', row['price'])
            loader.add_value('brand', 'LEGO')
            if row['sku'].lower() not in self.seen_ids:
                self.seen_ids.add(row['sku'].lower())
                yield loader.load_item()

import os
import csv
from scrapy.spider import BaseSpider

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class BunzlSpider(BaseSpider):
    name = 'bunzl-bunzl.com'

    filename = os.path.join(HERE, 'bunzl_products.csv')
    start_urls = ('file://' + filename,)

    def __init__(self, *args, **kwargs):
        super(BunzlSpider, self).__init__(*args, **kwargs)
        self.seen_ids = set()

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['SKU Number'].lower())
            loader.add_value('sku', row['SKU Number'])
            loader.add_value('brand', row['Category/Brand'].decode('utf8'))
            loader.add_value('category', row['Category/Brand'].decode('utf8'))
            loader.add_value('name', row['Product Name'].decode('utf8'))
            loader.add_value('url', row['Product website address'])
            loader.add_value('image_url', row['Image URL'])
            loader.add_value('price', extract_price(row['Retail Price']))
            loader.add_value('shipping_cost', extract_price(row['Shipping/Delivery Cost']))
            yield loader.load_item()

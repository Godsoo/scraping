import os
import csv
from cStringIO import StringIO
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class LegoSWSpider(BaseSpider):
    name = 'legodk-lego.com'

    lego_filename = os.path.join(HERE, 'legodk_products_old.csv')
    start_urls = ('file://' + lego_filename,)

    def __init__(self, *args, **kwargs):
        super(LegoSWSpider, self).__init__(*args, **kwargs)
        self.seen_ids = set()

    def parse(self, response):
        old_prices = {}
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            old_prices[row['Product No.']] = row

        with open(os.path.join(HERE, 'legodk_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('sku', row['Product No.'])
                loader.add_value('category', row['Theme'])
                loader.add_value('brand', 'LEGO')
                loader.add_value('name', row['Item Description English'].decode('utf8'))
                price = row.get('RRP price DKK')
                if not price:
                    old_product = old_prices.get(row['Product No.'])
                    price = '0.0'
                    identifier = row['Item no'].lower()
                    if old_product:
                        price = old_product.get('RRP price DKK')
                        identifier = old_product['Item no'].lower()

                    loader.add_value('price', price)
                    loader.add_value('identifier', identifier)
                else:
                    loader.add_value('price', price)
                    loader.add_value('identifier', row['Item no'].lower())
                if not loader.get_output_value('identifier') in self.seen_ids:
                    self.seen_ids.add(loader.get_output_value('identifier'))
                    yield loader.load_item()

import os
import csv
from cStringIO import StringIO
from scrapy import Spider
from product_spiders.config import DATA_DIR
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)


class ErfGoogleShoppingRSElectrical(Spider):
    name = 'erf-googleshopping.rselectricalsupplies'
    allowed_domains = ['google.co.uk']
    start_urls = ['file://' + os.path.join(DATA_DIR, 'erf_google_products.csv')]

    DEALER_NAME = '! RS Electrical Supplies'

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            dealer = row['dealer'].decode('utf-8')
            if dealer != self.DEALER_NAME:
                continue
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['identifier'])
            loader.add_value('sku', row['sku'])
            loader.add_value('name', row['name'].decode('utf8'))
            loader.add_value('price', row['price'])
            loader.add_value('url', row['url'].decode('utf-8'))
            loader.add_value('brand', row['brand'].decode('utf-8'))
            loader.add_value('shipping_cost', row['shipping_cost'])
            loader.add_value('dealer', row['dealer'].decode('utf-8'))
            yield loader.load_item()

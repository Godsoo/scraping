import csv
import os
from decimal import Decimal

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector

class LocalSpider (BaseSpider):

    start_urls = ['http://148.251.79.44/productspiders']
    path = ''

    handle_httpstatus_list = [403, 400, 500, 503]

    def parse(self, response):
        hxs = HtmlXPathSelector()
        with open(self.path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                product_loader = ProductLoader(item=Product(), selector=hxs)
                product_loader.add_value('identifier', row['identifier'].decode('utf8'))
                product_loader.add_value('sku', row['sku'].decode('utf8'))
                product_loader.add_value('name', row['name'].decode('utf8'))
                product_loader.add_value('url', row['url'].decode('utf8'))
                product_loader.add_value('price', row['price'])
                product_loader.add_value('brand', row['brand'].decode('utf8'))
                product_loader.add_value('category', row['category'].decode('utf8'))
                product_loader.add_value('dealer', row['dealer'].decode('utf8'))
                if row['stock']:
                    product_loader.add_value('stock', row['stock'])

                if hasattr(self, 'get_shipping_cost'):
                    price = Decimal(row['price']) if row['price'] else 0
                    product_loader.add_value('shipping_cost', str(self.get_shipping_cost(price)))
                elif row['shipping_cost']:
                    product_loader.add_value('shipping_cost', row['shipping_cost'])
                product_loader.add_value('image_url', row['image_url'].decode('utf8'))
                yield product_loader.load_item()

import os
import csv
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

from lecreusetitems import LeCreusetMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class LeCreusetSpider(BaseSpider):
    name = 'qatesting-lecreuset.com'

    lecruset_filename = os.path.join(HERE, 'lecreuset_products.csv')
    start_urls = ('file://' + lecruset_filename,)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['Barcode'].lower())
            loader.add_value('sku', row['SKU'])
            loader.add_value('name', row['Descritpion'].decode('utf'))
            loader.add_value('price', row['Price'])
            loader.add_value('brand', 'Le Creuset')
            loader.add_value('image_url', row['Product images'])
            product = loader.load_item()
            metadata = LeCreusetMeta()
            metadata['asin'] = row['ASIN']
            product['metadata'] = metadata
          
            yield product

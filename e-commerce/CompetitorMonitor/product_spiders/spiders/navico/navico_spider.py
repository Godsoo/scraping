import os
import csv
from scrapy.spider import BaseSpider

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from navicoitem import NavicoMeta

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class NavicoSpider(BaseSpider):
    name = 'navico.com'

    navico_filename = os.path.join(HERE, 'navico_products.csv')
    start_urls = ('file://' + navico_filename,)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['code'].lower())
            loader.add_value('sku', row['code'])
            loader.add_value('brand', row['brand'])
            loader.add_value('category', row['category'].decode('utf8'))
            loader.add_value('name', row['description'].decode('utf8'))
            loader.add_value('price', 0)
            product = loader.load_item()
            metadata = NavicoMeta()
            metadata['screen_size'] = row['screen size']
            product['metadata'] = metadata
            yield product

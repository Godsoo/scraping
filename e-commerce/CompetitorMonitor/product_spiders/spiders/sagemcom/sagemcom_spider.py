import os
import csv
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class SagemcomSpider(BaseSpider):
    name = 'sagemcom.com-dummy'
    allowed_domains = ['sagemcom.com']
    start_urls = ('http://www.sagemcom.com',)

    def parse(self, response):
        with open(os.path.join(HERE, 'sagemcom_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('identifier', row['identifier'].lower())
                loader.add_value('sku', row['sku'])
                loader.add_value('category', row['category'])
                loader.add_value('brand', row['brand'])
                loader.add_value('name', row['name'])
                loader.add_value('price', row['price'])
                yield loader.load_item()

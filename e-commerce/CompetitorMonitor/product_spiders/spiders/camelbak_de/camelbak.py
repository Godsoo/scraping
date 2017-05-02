import os
import csv
from product_spiders.base_spiders.primary_spider import PrimarySpider

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class CamelBakSpider(PrimarySpider):
    name = 'camelbak_de-camelbak.com'

    filename = os.path.join(HERE, 'camelbak_products.csv')
    start_urls = ('file://' + filename,)

    csv_file = 'camelbak.com_products.csv'

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            identifier = row['Manufacturer SKU']

            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', identifier.lower())
            loader.add_value('sku', identifier)
            loader.add_value('brand', 'Camelbak')
            loader.add_value('category', row['Product Category'].decode('utf8'))
            loader.add_value('name', row['Product Description'].decode('utf8'))
            loader.add_value('price', row['EURO SRP'].decode('utf8'))
            yield loader.load_item()

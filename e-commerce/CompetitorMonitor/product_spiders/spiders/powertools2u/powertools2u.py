import os
import csv
from scrapy.spider import BaseSpider

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO
from powertools2uitems import PowerTools2uMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class LegoFranceSpider(BaseSpider):
    name = 'powertools2u-powertools2u.co.uk'

    filename = os.path.join(HERE, 'powertools2u_products.csv')
    start_urls = ('file://' + filename,)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['Code'])
            loader.add_value('sku', row['Code'])
            loader.add_value('brand', row['Manufacturer'])
            categories = map(lambda x: x.strip(), row['Section'].split('/'))
            loader.add_value('category', categories)
            loader.add_value('name', row['Description'])
            loader.add_value('price', row['Price'])
            item = loader.load_item()

            metadata = PowerTools2uMeta()
            metadata['part_number'] = row['Part Number']
            metadata['warranty'] = row['Warranty']
            item['metadata'] = metadata

            yield item

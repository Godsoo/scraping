# -*- coding: utf-8 -*-

import os
import csv
from scrapy.spider import BaseSpider

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

from erfitems import ErfMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class ElectricalSuppliesSpider(BaseSpider):
    name = 'erf-electricalsupplies.co.uk'

    start_urls = ['https://www.electricalsupplies.co.uk/index.php/amfeed/main/download/file/BasicFeed.csv/']


    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            brand = row['Manufacturer'].strip()
            if brand.lower() in ('wse', 'unknown', 'unknowns'):
                continue

            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['SKU'].lower())
            loader.add_value('sku', row['SKU'])
            loader.add_value('brand', row['Manufacturer'])
            loader.add_value('category', row['Manufacturer'])
            loader.add_value('name', row['Name'].decode('utf-8'))
            loader.add_value('price', round(extract_price(row['Price']), 2))
            item = loader.load_item()
            
            metadata = ErfMeta()
            metadata['gtin'] = row['GTIN']
            item['metadata'] = metadata

            yield item
            

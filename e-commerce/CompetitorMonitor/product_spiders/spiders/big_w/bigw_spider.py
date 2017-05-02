import os
import csv

from scrapy import Spider
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)

HERE = os.path.abspath(os.path.dirname(__file__))


class BigWSpider(Spider):
    name = 'bigw-bigw.com.au'
    allowed_domains = ['bigw.com.au']

    start_urls = ['https://www.bigw.com.au']

    def parse(self, response):
        file_path = os.path.join(HERE, 'bigw_feed.csv')

        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('identifier', row['sku'])
                loader.add_value('sku', row['sku'])
                loader.add_value('brand', row['brand'])
                category_rows = ['category', 'sub_category', 'segment']
                categories = [row[k].strip() for k in category_rows]
                loader.add_value('category', categories)
                loader.add_value('name', row['name'])
                loader.add_value('price', row['price'])

                yield loader.load_item()

import os
import csv
import json
import xlrd
import paramiko

from scrapy.spiders import CSVFeedSpider
from scrapy.item import Item, Field
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class PowerhouseFitnessFeedMeta(Item):
    asin = Field()
    rrp = Field()


class PowerhouseFitnessSpider(CSVFeedSpider):
    name = 'powerhouse_fitness-powerhousefitness.co.uk'
    allowed_domains = ['powerhouse-fitness.co.uk']
    start_urls = ('http://www.powerhouse-fitness.co.uk/feeds/competitor_monitor_feed/powerhouse-competitor_monitor_feed.txt',)

    delimiter = '\t'
    headers = ['identifier', 'name', 'brand', 'category', 'price', 'rrp',
               'shipping_cost', '?', 'stock', 'url', 'image_url', 'asin']

    def parse_row(self, response, row):
        self.log(json.dumps(row))
        self.log(u' '.join(row.keys()))
        loader = ProductLoader(response=response, item=Product())
        loader.add_value('identifier', row['identifier'])
        loader.add_value('sku', row['identifier'])
        loader.add_value('name', row['name'])
        loader.add_value('brand', row['brand'])
        loader.add_value('category', row['category'])
        loader.add_value('price', row['price'])
        loader.add_value('shipping_cost', row['shipping_cost'])
        loader.add_value('stock', 0 if row['stock'] == 'out_of_stock' else None)
        loader.add_value('url', row['url'] + ('.php' if not row['url'].endswith('.php') else ''))
        loader.add_value('image_url', row['image_url'])
        product = loader.load_item()
        metadata = PowerhouseFitnessFeedMeta()
        metadata['rrp'] = row['rrp']
        metadata['asin'] = row['asin']
        product['metadata'] = metadata
        yield product



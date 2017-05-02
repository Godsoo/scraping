'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5479
'''

import os
import csv
from scrapy.spider import Spider
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.lib.schema import SpiderSchema

HERE = os.path.abspath(os.path.dirname(__file__))


class Maplin(Spider):
    name = 'maplin-maplin'
    allowed_domains = ['maplin.co.uk']
    
    file_path = HERE + '/products.csv'

    def start_requests(self):
        url = 'http://www.maplin.co.uk/search?text=%s'
        with open(self.file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Maplin part code']:
                    yield(Request(url % row['Maplin part code'],
                          meta = {'row': row}))
                    
    def parse(self, response):
        schema = SpiderSchema(response)
        pdata = schema.get_product()
        row = response.meta['row']
        
        loader = ProductLoader(Product(), response=response)
        loader.add_value('identifier', pdata['sku'])
        loader.add_value('url', response.url)
        loader.add_value('name', pdata['name'])
        loader.add_value('price', pdata['offers']['properties']['price'])
        loader.add_value('sku', pdata['sku'])
        metadata = {'mpn': row['Manufacturer part code']}
        loader.add_value('category', row['Category'])
        loader.add_value('image_url', pdata['image'])
        loader.add_value('brand', row['Manufacturer name'])    
        item = loader.load_item()
        item['metadata'] = metadata
        yield item

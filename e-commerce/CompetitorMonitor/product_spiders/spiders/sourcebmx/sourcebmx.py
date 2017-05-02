from scrapy.spider import BaseSpider

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)

import csv
from cStringIO import StringIO


class SourcebmxFeedSpider(BaseSpider):
    name = 'sourcebmx-feed'
    allowed_domains = ['sourcebmx.com']
    start_urls = ('https://www.sourcebmx.com/Feed.aspx?FeedID=1',)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body), delimiter='\t')
        for product in reader:
            product_loader = ProductLoader(item=Product(), response=response)
            options = ''
            if product['size']:
                options += ' - ' + product['size']
            if product['color']:
                options += ' - ' + product['color']
            if product['material']:
                options += ' - ' + product['material']
            if product['pattern']:
                options += ' - ' + product['pattern']
            name = product['title']
            if product['product_type']:
                name += ' - ' + product['product_type']
            if options:
                name += ' - ' + options
            product_loader.add_value('name', name)
            product_loader.add_value('url', product['link'])
            product_loader.add_value('image_url', product['image_link'])
            product_loader.add_value('category', product['google_product_category'].split('>')[-1].strip())
            product_loader.add_value('brand', product['brand'])
            product_loader.add_value('price', product['price'])
            product_loader.add_value('sku', product['mpn'])
            product_loader.add_value('identifier', product['id'])
            product_loader.add_value('shipping_cost', product['shipping'])
            if product['availability'] == 'out of stock':
                product_loader.add_value('stock', 0)
            product = product_loader.load_item()
            yield product

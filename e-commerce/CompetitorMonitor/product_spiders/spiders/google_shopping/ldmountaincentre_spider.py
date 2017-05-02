import os
import csv

from scrapy.spider import BaseSpider

from product_spiders.items import Product

from decimal import Decimal

HERE = os.path.abspath(os.path.dirname(__file__))


class LdMountainCentreSpider(BaseSpider):
    name = 'google_shopping-ldmountaincentre.com'
    allowed_domains = ['ldmountaincentre.com']

    start_urls = ('http://www.ldmountaincentre.com/',)

    def parse(self, response):
        with open(os.path.join(HERE, 'product_skus.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                p = Product()
                p['url'] = row['url']
                p['name'] = row['name']
                p['sku'] = row['sku']
                p['price'] = Decimal(row['price'] or 0)
                p['identifier'] = row['identifier']
                p['image_url'] = row['image_url']
                p['category'] = row['category']
                p['shipping_cost'] = row['shipping_cost']

                yield p


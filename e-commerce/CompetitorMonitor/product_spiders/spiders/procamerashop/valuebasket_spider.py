import os
import csv
import string
from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.fuzzywuzzy import process

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from decimal import Decimal

HERE = os.path.abspath(os.path.dirname(__file__))

class ValueBasketSpider(BaseSpider):
    name = 'valuebasket.com'
    allowed_domains = ['valuebasket.com']
    start_urls = ['http://www.valuebasket.com/en_GB']

    def parse(self, response):
        with open(os.path.join(HERE, 'valuebasket.csv')) as f:
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

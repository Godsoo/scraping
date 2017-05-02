import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode

import csv

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class KeterSpider(BaseSpider):
    name = 'keter.com'
    allowed_domains = ['keter.com']
    start_urls = ('http://www.keter.com',)
    metadata_rules = {}

    def parse(self, response):
        f = open(os.path.join(HERE, 'keter.csv'))
        reader = csv.DictReader(f)
        for row in reader:
            loader = ProductLoader(item=Product(), selector=HtmlXPathSelector())
            loader.add_value('name', row['Title'].decode('utf8'))
            loader.add_value('identifier', row['SKU'])
            loader.add_value('sku', row['SKU'])
            loader.add_value('brand', 'keter')
            loader.add_value('price', 0)

            yield loader.load_item()
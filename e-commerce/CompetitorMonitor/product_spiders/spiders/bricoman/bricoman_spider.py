import re
import csv
import os
import copy
import shutil

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.spiders.BeautifulSoup import BeautifulSoup

HERE = os.path.abspath(os.path.dirname(__file__))

class BricomanSpider(BaseSpider):
    name = 'bricoman.it'
    allowed_domains = ['bricoman.it']
    start_urls = ('http://www.bricoman.it',)

    def parse(self, response):
        with open(os.path.join(HERE, 'bricoman_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('sku', row['bricoman_code'])
                loader.add_value('identifier', row['bricoman_code'])
                loader.add_value('name', row['name'])
                loader.add_value('price', row['price'])
                yield loader.load_item()

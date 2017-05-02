import csv
import re
import urllib
import logging
import os

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class KentCaSpider(BaseSpider):
    name = 'kent.ca-kent.ca'
    allowed_domains = ['kent.ca']
    # user_agent = 'Googlebot/2.1 (+http://www.google.com/bot.html)'
    start_urls = (u'http://www.kent.ca', )

    def __init__(self, *args, **kwargs):
        super(KentCaSpider, self).__init__(*args, **kwargs)
        with open(os.path.join(HERE, 'products.csv')) as f:
            reader = csv.DictReader(f)
            self.products = [row for row in reader if row.get('homedepot_url')]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for row in self.products:
            product_loader = ProductLoader(item=Product(), response=response)
            product_loader.add_value('name', row.get('title').decode('utf8'))
            # product_loader.add_xpath('sku', u'//span[@class="store-sku"]/text()')
            product_loader.add_value('sku', row.get('sku'))
            # async JS
            #product_loader.add_xpath('price', u'//p[@class="offer-price"]/text()')
            product_loader.add_value('price', row.get('our_price').replace(u'.', '').replace(u',', u'.'))
            product_loader.add_value('url', row.get('kent_url'))
            yield product_loader.load_item()

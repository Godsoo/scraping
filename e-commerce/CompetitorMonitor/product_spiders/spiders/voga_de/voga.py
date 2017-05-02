import re
import csv
from StringIO import StringIO

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.spiders.voga_uk.vogaitems import VogaMeta


class VogaSpider(BaseSpider):
    name = 'voga_de-voga.com'
    allowed_domains = ['goldenfeeds.com']
    start_urls = ()

    def start_requests(self):
        yield Request('http://feedshare.goldenfeeds.com/voga/intelligenteye/voga_de_intelligenteye.csv')

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))

        for row in reader:
            product_loader = ProductLoader(item=Product(), response=response)
            product_loader.add_value('url', row['Product page URL'].decode('utf-8'))
            product_loader.add_value('name', row['Product name'].decode('utf-8'))
            product_loader.add_value('image_url', row['Image URL'].decode('utf-8'))
            product_loader.add_value('identifier', row['Unique product code'].decode('utf-8'))
            product_loader.add_value('sku', row['sku'].decode('utf-8'))
            product_loader.add_value('price', str(float(row['Price'].decode('utf-8'))))
            product_loader.add_value('category', row['Category'].decode('utf-8'))
            product_loader.add_value('brand', row['Brand'].decode('utf-8'))
            product_loader.add_value('shipping_cost', row['Shipping cost'])
            item = product_loader.load_item()
            yield item

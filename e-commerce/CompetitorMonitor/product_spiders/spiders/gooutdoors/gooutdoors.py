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


class GoOutdoorsSpider(BaseSpider):
    name = 'gooutdoors-gooutdoors.com'
    allowed_domains = ['gooutdoors.com']
    start_urls = ('http://www.gooutdoors.com',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        with open(os.path.join(HERE, 'gooutdoors_products.csv')) as f:
            reader = csv.DictReader(f)
            for product in reader:
                loader = ProductLoader(Product(), response=response, selector=hxs)
                loader.add_value('name', product['title'].decode('utf-8'))
                loader.add_value('url', product['link'])
                loader.add_value('brand', product['brand'].decode('utf-8'))
                loader.add_value('identifier', product['id'])
                loader.add_value('sku', product['mpn'])
                loader.add_value('image_url', product['image_link'])
                loader.add_value('category', product['product_type'].decode('utf-8').split('>')[-2].strip())
                loader.add_value('price', product['price'].replace(',', '.'))
                yield loader.load_item()

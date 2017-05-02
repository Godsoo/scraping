from time import sleep
import random
import os
import csv
import json
import shutil
from random import randint
from datetime import datetime

from product_spiders.phantomjs import PhantomJS

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from selenium.common.exceptions import TimeoutException

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from tigerchefitems import TigerChefMeta

from product_spiders.config import (
    PROXY_SERVICE_HOST,
    PROXY_SERVICE_USER,
    PROXY_SERVICE_PSWD,
)

import requests
from requests.auth import HTTPBasicAuth

USER_AGENTS = '''Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/537.75.14
Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36
Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36
Mozilla/5.0 (Windows NT 6.1; WOW64; rv:28.0) Gecko/20100101 Firefox/28.0
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36
Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:28.0) Gecko/20100101 Firefox/28.0
Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36
Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36
Mozilla/5.0 (Windows NT 6.1; WOW64; rv:29.0) Gecko/20100101 Firefox/29.0
Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko
Mozilla/5.0 (Windows NT 6.1; rv:28.0) Gecko/20100101 Firefox/28.0
Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36
Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36'''

MATCHED_BRANDS = '''https://www.instawares.com/F-Dick.0.2107.0.0.htm
https://www.instawares.com/Hamilton-Beach.0.165.0.0.htm
https://www.instawares.com/Turbo-Air.0.1664.0.0.htm
https://www.instawares.com/Browne-Halco.0.2696.0.0.htm
https://www.instawares.com/Victory-Refrigeration-Company.0.566.0.0.htm
https://www.instawares.com/Detecto.0.525.0.0.htm
https://www.instawares.com/Dynamic.0.1914.0.0.htm
https://www.instawares.com/Win-Holt-Equipment-Group.0.369.0.0.htm
https://www.instawares.com/Nemco.0.550.0.0.htm
https://www.instawares.com/Chef-Revival-American-Promotional.0.4433.0.0.htm
https://www.instawares.com/Cardinal-International.0.3255.0.0.htm
https://www.instawares.com/Rubbermaid-Commercial.0.303.0.0.htm
https://www.instawares.com/Dispense-Rite.0.2074.0.0.htm
https://www.instawares.com/Advance-Tabco.0.562.0.0.htm
https://www.instawares.com/Update-International.0.1900.0.0.htm
https://www.instawares.com/Magikitchn.0.1975.0.0.htm
https://www.instawares.com/Winco-DWL.0.485.0.0.htm
https://www.instawares.com/Ice-O-Matic.0.2173.0.0.htm
https://www.instawares.com/Walco.0.1730.0.0.htm
https://www.instawares.com/Rubbermaid-Home-Products.0.1630.0.0.htm
https://www.instawares.com/Bakers-Pride.0.604.0.0.htm
https://www.instawares.com/Bloomfield.0.43.0.0.htm
https://www.instawares.com/Continental-Refrigerator.0.691.0.0.htm
https://www.instawares.com/Amana.0.2029.0.0.htm
https://www.instawares.com/Dexter-Russell.0.304.0.0.htm
https://www.instawares.com/Wells.0.364.0.0.htm
https://www.instawares.com/Toastmaster.0.1838.0.0.htm
https://www.instawares.com/GET-Enterprises-Inc.0.150.0.0.htm
https://www.instawares.com/Hoover.0.176.0.0.htm
https://www.instawares.com/Eastern-Tabletop.0.2081.0.0.htm
https://www.instawares.com/Vollrath.0.4062.0.0.htm'''

here = os.path.abspath(os.path.dirname(__file__))

class InstawaresSpider(BaseSpider):
    name = 'instawares.com'
    allowed_domains = ['instawares.com', 'google.com']
    start_urls = ['http://google.com']

    products_file = os.path.join(here, 'instawares.csv')
    all_products_file = os.path.join(here, 'instawares_products.csv')
    all_meta_file = os.path.join(here, 'instawares.json')

    seen = set()

    def __init__(self, *args, **kwargs):
        super(InstawaresSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self.prod_data = {}
        self.all_prod_data = {}
        self.sold_as = {}
        if os.path.exists(self.products_file):
            with open(self.products_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.prod_data[row['identifier']] = row

        if os.path.exists(self.all_products_file):
            with open(self.all_products_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.all_prod_data[row['identifier']] = row

        if os.path.exists(self.all_meta_file):
            with open(self.all_meta_file) as f:
                data = json.load(f)
                for row in data:
                    self.sold_as[row['identifier']] = row['metadata'].get('sold_as')

    def spider_closed(self, spider):

        self.log('Loading remaining products')
        for p in self.all_prod_data:
            if p in seen:
                continue
            pr = self.all_prod_data[p]
            loader = ProductLoader(item=Product(), selector=HtmlXPathSelector())
            loader.add_value('identifier', pr['identifier'].decode('utf8'))
            loader.add_value('brand', pr['brand'].decode('utf8'))
            loader.add_value('category', pr['category'].decode('utf8'))
            loader.add_value('url', pr['url'].decode('utf8'))
            loader.add_value('name', pr['name'].decode('utf8'))
            loader.add_value('sku', pr['sku'].decode('utf8'))
            loader.add_value('image_url', pr['image_url'].decode('utf8'))
            loader.add_value('price', pr['price'])
            product = loader.load_item()
            if p in self.sold_as:
                meta = TigerChefMeta()
                meta['sold_as'] = self.sold_as[p].decode('utf8')
                product['metadata'] = meta

            yield product

        shutil.copy('data/%s_products.csv' % spider.crawl_id, self.all_products_file)

    def start_requests(self):
        brands = MATCHED_BRANDS.split('\n')
        for brand in brands:
            yield Request(brand+'?Rpp=5000')

    def parse(self, response):
        root_url = 'https://www.instawares.com'

        hxs = HtmlXPathSelector(response)
        products = self.get_products(hxs, response.url)

        self.log('%s products found' % len(products))
        for product in products:
            if product['identifier'] not in self.seen:
                self.seen.add(product['identifier'])
                yield product

    def get_products(self, hxs, url):
        root_url = 'https://www.instawares.com'
        res = []
        products = hxs.select('//ol[starts-with(@class, "productListResultOL")]/li')
        # self.log('%s products found' % len(products))
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('name', './/div[@class="listResultsDescriptionDiv"]/a/text()')
            loader.add_xpath('identifier', './/div[@class="listResultsDescriptionDiv"]/dl/dd[1]/text()')
            loader.add_xpath('price', './/div[@class="listResultPrice"]/text()')
            loader.add_xpath('brand', './/div[@class="listResultsDescriptionDiv"]/dl/dt[contains(text(), "By")]/following-sibling::dd/text()')
            url = product.select('.//div[@class="listResultsDescriptionDiv"]/a/@href').extract()[0]
            loader.add_value('url', urljoin_rfc(root_url, url))
            if loader.get_output_value('identifier') in self.prod_data:
                row = self.prod_data[loader.get_output_value('identifier')]
                loader.add_value('brand', row['brand'].decode('utf8'))
                loader.add_value('category', row['category'].decode('utf8'))
                loader.add_value('sku', row['sku'].decode('utf8'))

            image_url = product.select('.//img[@class="productimagelarge"]/@src').extract()
            if image_url:
                image_url = image_url[0]
                loader.add_value('image_url', urljoin_rfc(root_url, image_url))

            p = loader.load_item()
            if p['identifier'] in self.sold_as:
                sold_as = self.sold_as[p['identifier']]
                metadata = TigerChefMeta()
                metadata['sold_as'] = sold_as
                p['metadata'] = metadata

            res.append(loader.load_item())

        if not res and hxs.select('//h1[@class="productName fn"]/text()'):
            loader = ProductLoader(selector=hxs, item=Product(), spider_name=self.name)
            loader.add_value('url', url)
            loader.add_xpath('name', '//h1[@class="productName fn"]/text()')
            loader.add_xpath('price', '//li[@class="price"]//text()')
            loader.add_xpath('sku', '//div[starts-with(@class, "specificationContent")]' +
                                    '//td[contains(text(), "Manufacturer ID")]/following-sibling::td/text()')
            loader.add_xpath('identifier', '//td[@itemprop="productID"]/text()')

            brand = hxs.select('//td[@class="brand"]/text()').extract()
            if not brand:
                self.log("ERROR brand not found")
            else:
                loader.add_value("brand", brand[0].strip())

            image_url = hxs.select('//div[@class="productImageDiv"]/a/img/@src').extract()
            if not image_url:
                self.log("ERROR image_url not found")
            else:
                loader.add_value("image_url", urljoin_rfc(root_url, image_url[0]))

            category = hxs.select('(//ol[@class="breadcrumbOL"]/a)[last()]/text()').extract()
            if not category:
                self.log("ERROR category not found")
            else:
                loader.add_value("category", category[0].strip())

            sold_as = hxs.select('//dl[@class="soldAsPackedAsDL"]/dd[1]/text()').extract()
            product = loader.load_item()

            metadata = TigerChefMeta()
            metadata['sold_as'] = sold_as[0].strip() if sold_as else '1 ea'
            product['metadata'] = metadata

            if product.get('identifier'):
                res.append(loader.load_item())

        return res

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

class HomedepotCaSpider(BaseSpider):
    name = 'kent.ca-homedepot.ca'
    allowed_domains = ['homedepot.ca']
#    user_agent = 'Googlebot/2.1 (+http://www.google.com/bot.html)'

    def start_requests(self):
        with open(os.path.join(HERE, 'products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row['homedepot_url']
                if url:
                    yield Request(url, meta={'sku': row['sku']}, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_xpath('name', u'//h1/text()[last()]')
        # product_loader.add_xpath('sku', u'//span[@class="store-sku"]/text()')
        product_loader.add_value('sku', response.meta['sku'])
        # async JS
        #product_loader.add_xpath('price', u'//p[@class="offer-price"]/text()')
        product_loader.add_value('url', response.url)
        product = product_loader.load_item()

        price_url = 'http://www.homedepot.ca/async-fetch-regional-price?storeId=7148&pnList='
        price_url += product['url'].split('/')[-1]
        yield Request(price_url, meta={'product': product}, callback=self.parse_price)

    def parse_price(self, response):
        product = response.meta['product']
        #reg-price="349.0" promo-price="349.0"
        match = re.search(u'promo-price="([\d.,]+)"', response.body)
        if not match: 
            match = re.search(u'reg-price="([\d.,]+)"', response.body)
        # contains negative price if price not available, regexp does not patch negative values
        if match:
            product['price'] = match.group(1)
        else:
            product['price'] = '0.00'
        yield product

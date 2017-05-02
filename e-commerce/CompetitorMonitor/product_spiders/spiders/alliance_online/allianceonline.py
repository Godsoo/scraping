import re
import os
from decimal import Decimal

# from scrapy.contrib.spiders import XMLFeedSpider
from scrapy.spider import BaseSpider
# from scrapy.selector import HtmlXPathSelector
from scrapy.selector import XmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
import hashlib

import csv
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from scrapy import log
from scrapy.shell import inspect_response

from urlparse import urljoin

HERE = os.path.abspath(os.path.dirname(__file__))

class AllianceonlineSpider(BaseSpider):
    name = 'allianceonline.co.uk'
    # allowed_domains = ['allianceonline.co.uk']
    start_urls = ['http://www.allianceonline.co.uk/service/GoogleFeed.xml']
    # start_urls = ['https://www.yahoo.com']

    def parse(self, response):
        # inspect_response(response, self)
        # return
        # hxs = HtmlXPathSelector(response)
        # file_path = "d:/work/GoogleFeed.xml"
        # f = open(file_path)
        # xxs = XmlXPathSelector(text=f.read())
        xxs = XmlXPathSelector(response)
        for sel in xxs.select('//channel/item'):  # ##
            loader = ProductLoader(item=Product(), response=response)
            tmp = sel.select('link/text()').extract()
            if tmp:
                loader.add_value('url', tmp[0])
            # ID
            tmp = sel.select('*[name()="g:id"]/text()').extract()
            if tmp:
                loader.add_value('identifier', tmp[0])
            # Sku
            tmp = sel.select('*[name()="g:id"]/text()').extract()
            if tmp:
                loader.add_value('sku', tmp[0])
            # Name
            tmp = sel.select('title/text()').extract()
            if tmp:
                loader.add_value('name', tmp[0])
            # price
            tmp = sel.select('*[name()="g:sale_price"]/text()').extract()
            if not tmp:
                tmp = sel.select('*[name()="g:price"]/text()').extract()
            if tmp:
                price = round(extract_price(tmp[0]) / Decimal('1.20'), 2)
                loader.add_value('price', price)
            # image_url
            tmp = sel.select('*[name()="g:image_link"]/text()').extract()
            if tmp:
                loader.add_value('image_url', tmp[0])
            # Brand
            tmp = sel.select('*[name()="g:brand"]/text()').extract()
            if tmp and tmp[0] != 'Alliance':
                loader.add_value('brand', tmp[0])
            # category
            tmp = sel.select('*[name()="g:product_type"]/text()').extract()
            if tmp:
                try:
                    loader.add_value('category', tmp[0].split('>')[1].strip())
                except:
                    loader.add_value('category', tmp[0].strip())
            # shipping_cost
            price = loader.load_item()['price']
            if price and price < 50.00:
                loader.add_value('shipping_cost', 5.90)
            # stock
            tmp = sel.select('*[name()="g:availability"]/text()').extract()
            if tmp and tmp[0] == 'in stock':
                loader.add_value('stock', 1)
            else:
                loader.add_value('stock', 0)

            yield loader.load_item()


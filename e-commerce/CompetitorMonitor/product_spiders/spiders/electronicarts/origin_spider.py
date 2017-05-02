import os
import re
import json
import csv
import itertools
import urlparse

from copy import deepcopy

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class OriginSpider(BaseSpider):
    name = 'electronicarts-origin.com'
    allowed_domains = ['origin.com']

    start_urls = ['https://www.origin.com']

    def start_requests(self):
        with open(os.path.join(HERE, 'EAMatches.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield Request(row['Origin'], meta={'sku': row['sku']})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        meta = response.meta

        loader = ProductLoader(response=response, item=Product())
        identifier = hxs.select('//a[contains(@class, "btn-large")]/@href').extract()[0].split('/')[-1]
        loader.add_value('identifier', identifier)
        name = hxs.select('//div[@class="span24"]/h1/text()').extract()[0].strip()
        loader.add_value('name', name)
        loader.add_value('sku', meta['sku'])
        price = hxs.select('//p[@class="actual-price"]/text()').extract()
        price = price[0] if price else '0'
        loader.add_value('price', extract_price_eu(price))
        loader.add_value('url', response.url)
        loader.add_xpath('image_url', '//img[@class="main-packart"]/@src')
        yield loader.load_item()


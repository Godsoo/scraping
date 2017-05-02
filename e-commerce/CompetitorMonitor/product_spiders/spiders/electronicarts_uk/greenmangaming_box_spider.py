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

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class GreenmanGamingSpider(BaseSpider):
    name = 'electronicarts-uk-greenmangaming.com-box'
    allowed_domains = ['greenmangaming.com']

    start_urls = ['http://www.greenmangaming.com']

    def start_requests(self):
        with open(os.path.join(HERE, 'EAMatches.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['GreenmanGaming - PC Box']!="No match":
                    yield Request(row['GreenmanGaming - PC Box'], meta={'sku': row['sku']})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        meta = response.meta

        loader = ProductLoader(response=response, item=Product())
        identifier = response.url.split('/')[-2]
        loader.add_value('identifier', identifier)
        name = hxs.select('//h1[@class="prod_det"]/text()').extract()[0]
        loader.add_value('name', name)
        loader.add_value('sku', meta['sku'])
        price = hxs.select('//strong[@class="curPrice"]/text()').extract()
        price = price[0] if price else '0'
        loader.add_value('price', extract_price(price))
        loader.add_value('url', response.url)
        yield loader.load_item()


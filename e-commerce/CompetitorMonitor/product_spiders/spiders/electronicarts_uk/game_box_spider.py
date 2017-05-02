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

class GameSpider(BaseSpider):
    name = 'electronicarts-uk-game.co.uk-box'
    allowed_domains = ['game.co.uk']

    start_urls = ['http://www.game.co.uk']

    def start_requests(self):
        with open(os.path.join(HERE, 'EAMatches.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Game - PC Box']!="No match":
                    yield Request(row['Game - PC Box'], meta={'sku': row['sku']})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        meta = response.meta

        loader = ProductLoader(response=response, item=Product())
        identifier = hxs.select('//ul[contains(@class, "mint")]//input[@name="productId_1"]/@value').extract()[0]
        loader.add_value('identifier', identifier)
        name = hxs.select('//div[@class="productHeader"]/h1/text()').extract()[0].strip()
        loader.add_value('name', name)
        loader.add_value('sku', meta['sku'])
        price =  ''.join(hxs.select('//ul[contains(@class, "mint")]/li[contains(@class, "price")]//text()').extract()).strip()
        price = price if price else '0'
        loader.add_value('price', extract_price(price))
        loader.add_value('url', response.url)
        out_of_stock = hxs.select('//div[@class="outOfStock"]')
        if out_of_stock:
            loader.add_value('stock', 0)
        loader.add_xpath('image_url', '//img[@class="mainImage"]/@src')
        yield loader.load_item()


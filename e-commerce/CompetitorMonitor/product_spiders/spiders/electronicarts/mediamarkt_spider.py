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

class MediamarktSpider(BaseSpider):
    name = 'electronicarts-mediamarkt.com'
    allowed_domains = ['mediamarkt.de']

    start_urls = ['http://games-download.mediamarkt.de']

    def start_requests(self):
        with open(os.path.join(HERE, 'EAMatches.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['mediamarkt'] != 'No matches':
                    yield Request(row['mediamarkt'], meta={'sku': row['sku']})

        extra_products = [
            'http://www.mediamarkt.de/mcs/product/Battlefield-Hardline-Action-PC,48353,464590,1335377.html?langId=-3',
            'http://www.mediamarkt.de/mcs/product/FIFA-15-Sport-PC,48353,464590,1335437.html?langId=-3',
            'http://games-download.mediamarkt.de/catalog/product/view/483322',
            'http://games-download.mediamarkt.de/catalog/product/view/483321',
        ]

        for url in extra_products:
            yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        meta = response.meta

        loader = ProductLoader(response=response, item=Product())
        identifier = hxs.select('//dd[@itemprop="sku"]/text()').extract()
        if identifier:
            identifier = identifier[0]
        else:
            identifier = response.url.split('/')[-1]
        loader.add_value('identifier', identifier)
        name = hxs.select('//h1[@class="detail__title"]/text()').extract()
        if not name:
            name = hxs.select('//h1[@itemprop="name"]/text()').extract()

        loader.add_value('name', name[0].strip())
        price = hxs.select('//img[@class="buybox__pricetag"]/@alt|//*[@itemprop="price"]/text()').extract()
        if price:
            price = price[0]
        else:
            price = '0'
        sku = meta.get('sku')
        if sku:
            loader.add_value('sku', meta['sku'])
        loader.add_value('price', extract_price_eu(price))
        loader.add_value('url', response.url)
        loader.add_xpath('image_url', '//div[contains(@class, "product-images")]/img/@src|//img[@itemprop="image"]/@src',
                         lambda imgs: urljoin_rfc(base_url, imgs[0]))
        yield loader.load_item()


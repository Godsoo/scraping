import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
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

import itertools
import json
import copy
import lxml

HERE = os.path.abspath(os.path.dirname(__file__))

class RitualsdeSpider(BaseSpider):
    name = 'the_body_shop-rituals_de'
    #download_delay = 1
    allowed_domains = ['rituals.com']
    #start_urls = ['http://www.yves-rocher.co.uk/control/main/']
    start_urls = [
        'https://eu.rituals.com/de-de/bodylotion-feuchtigkeitscreme/mei-dao-3253.html#q=3253&start=1',
        'https://eu.rituals.com/de-de/balsam/ginkgos-secret-9100.html?q=Ginkgo%27s%20Secret',
        'https://eu.rituals.com/de-de/duschgel-duschpaste/hammam-olive-secret-9815.html#start=3',
        'https://eu.rituals.com/de-de/lippenstift/lipstick--china-red-2519.html#start=2',
        'https://eu.rituals.com/de-de/camouflage/lighten-up-2-2572.html?q=Lighten%20Up%202',
        'https://eu.rituals.com/de-de/hydrating/24h-hydrating-gel-cream-6341.html?q=24h%20Hydrating%20Gel%20Cream',
        'https://eu.rituals.com/de-de/anti-age/skin-energy-serum-6349.html?q=Skin%20Energy%20Serum',
        'https://eu.rituals.com/de-de/gesichtscreme-maenner/samurai-energize-9775.html?q=Samurai%20Energize',
    ]
    #cookie_num = 0
    #brands = []
    id_seen = []

    def parse(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)

        tmp = hxs.select('//div[@class="sku"]/h2/span[@class="value"]/text()').extract()
        if tmp:
            loader.add_value('identifier', tmp[0].strip())
            loader.add_value('sku', tmp[0].strip())
        else:
            log.msg('### No product ID at '+response.url, level=log.INFO)
            return
        #tmp = hxs.select('//input[@name="productId"]/@value').extract()
        #if tmp:
        #    loader.add_value('sku', tmp[0])
        name = ''
        tmp = hxs.select('//h1[@itemprop="name"]/text()').extract()
        if tmp:
            name = tmp[0].strip()
            loader.add_value('name', name)
        else:
            log.msg('### No name at '+response.url, level=log.INFO)
        #price
        price = 0
        stock = 0
        tmp = hxs.select('//span[@itemprop="price"]/text()').extract()
        if tmp:
            price = extract_price(tmp[0].replace('.','').replace(',','.').strip())
            loader.add_value('price', price)
            #stock = 1
        #stock
        #stock = 0
        #tmp = hxs.select('//div[@id="col2"]//span[text()="In den Warenkorb"]')
        #if tmp:
        if price:
            stock = 1
        loader.add_value('stock', stock)
        #image_url
        tmp = hxs.select('//img[@itemprop="image"]/@src').extract()
        if tmp:
            #url = urljoin(response.url, tmp[0].strip())
            loader.add_value('image_url', tmp[0])
        #brand
        # tmp = hxs.select('//div[@class="primary-logo"]//img/@alt').extract()
        # if tmp:
        #     loader.add_value('brand', tmp[0].upper())
        loader.add_value('brand', 'Rituals')
        #category
        # tmp = hxs.select('//ol[contains(@class,"breadcrumb")]/li/a/text()').extract()
        # if len(tmp)>1:
        #     for s in tmp[1:]:
        #         loader.add_value('category', s)
        category = hxs.select('//*[@id="add-to-cart"]/@data-category').extract()
        category = category[0] if category else ''
        loader.add_value('category', category)
        #shipping_cost
        #if price<30:
        #    loader.add_value('shipping_cost', 3.95)
        #elif price<50:
        #    loader.add_value('shipping_cost', 5.95)

        product = loader.load_item()
        #metadata = {}
        #tmp = hxs.select('//div[@id="col2"]//div[@class="promo"]/img/@alt').extract()
        #if tmp:
        #    metadata['promotion'] = []
        #    for s in tmp:
        #        s = s.replace('picto-','')
        #        metadata['promotion'].append(s)
        #if metadata:
        #    product['metadata'] = metadata

        return product


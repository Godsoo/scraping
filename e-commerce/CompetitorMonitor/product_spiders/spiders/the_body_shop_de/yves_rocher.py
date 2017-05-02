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
from scrapy.item import Item, Field

from urlparse import urljoin

import itertools
import json
import copy
import lxml

HERE = os.path.abspath(os.path.dirname(__file__))

class YMeta(Item):
    promotions = Field()



class YvesrocherdeSpider(BaseSpider):
    name = 'thebodyshop_de-yves-rocher.co.uk'
    #download_delay = 1
    allowed_domains = ['yves-rocher.de']
    #start_urls = ['http://www.yves-rocher.co.uk/control/main/']
    start_urls = [
        'http://www.yves-rocher.de/control/product/~category_id=4300/~product_id=63620',
        'http://www.yves-rocher.de/control/product/~category_id=4350/~product_id=86534',
        'http://www.yves-rocher.de/control/product/~category_id=6000/~product_id=03413',
        'http://www.yves-rocher.de/control/product/~category_id=3450/~product_id=22061',
        'http://www.yves-rocher.de/control/product/~category_id=3400/~product_id=88436',
        'http://www.yves-rocher.de/control/product/~category_id=2500/~product_id=44557',
        'http://www.yves-rocher.de/control/product/~category_id=B1500/~product_id=31749',
        'http://www.yves-rocher.de/control/product/~category_id=6100/~product_id=19013',
        'http://www.yves-rocher.de/control/product/~category_id=1064/~product_id=66838',
        'http://www.yves-rocher.de/control/product/~category_id=7050/~product_id=00408',
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

        tmp = hxs.select('//div[@id="col2"]//input[contains(@id,"product_minidetail_")]/@value').extract()
        if tmp:
            loader.add_value('identifier', tmp[0])
            loader.add_value('sku', tmp[0])
        else:
            log.msg('### No product ID at '+response.url, level=log.INFO)
            return
        #tmp = hxs.select('//input[@name="productId"]/@value').extract()
        #if tmp:
        #    loader.add_value('sku', tmp[0])
        name = ''
        tmp = hxs.select('//div[@id="col2"]//h1[@class="titre"]/text()').extract()
        if tmp:
            name = tmp[0].strip()
            loader.add_value('name', name)
        else:
            log.msg('### No name at '+response.url, level=log.INFO)
        #price
        price = 0
        stock = 0
        tmp = hxs.select('//div[@id="col2"]//span[@class="prix"]/text()').extract()
        if tmp:
            price = extract_price(tmp[0].replace('.','').replace(',','.').strip())
            loader.add_value('price', price)
            #stock = 1
        #stock
        #stock = 0
        tmp = hxs.select('//div[@id="col2"]//span[text()="In den Warenkorb"]')
        if tmp:
            stock = 1
        loader.add_value('stock', stock)
        #image_url
        tmp = hxs.select('//div[@id="col1"]//div[contains(@class,"product")]/img/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0].strip())
            loader.add_value('image_url', url)
        #brand
        tmp = hxs.select('//div[@id="col2"]//td[@class="catName"]/a/text()').extract()
        if tmp:
            loader.add_value('brand', tmp[0].upper())
        #category
        tmp = hxs.select('//div[@id="breadcrumb"]/h2/a/text()').extract()
        if tmp:
            for s in tmp:
                loader.add_value('category', s)
        #shipping_cost
        if price<30:
            loader.add_value('shipping_cost', 3.95)
        #elif price<50:
        #    loader.add_value('shipping_cost', 5.95)

        product = loader.load_item()
        metadata = YMeta()
        tmp = hxs.select('//div[@id="col2"]//div[@class="promo"]/img/@alt').extract()
        if tmp:
            metadata['promotions'] = []
            for s in tmp:
                s = s.replace('picto-','')
                metadata['promotions'].append(s)
            metadata['promotions'] = ','.join(metadata['promotions'])
        if metadata:
            product['metadata'] = metadata

        return product

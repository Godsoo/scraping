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

HERE = os.path.abspath(os.path.dirname(__file__))

class SelfridgesSpider(BaseSpider):
    name = 'lecreuset-selfridges.com'
    #download_delay = 3
    allowed_domains = ['selfridges.com']
    start_urls = ['http://www.selfridges.com/en/le-creuset/home-tech/']
    cookie_num = 0
    #brands = []
    id_seen = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//div[@class="products"]//div[@class="productContainer"]/a[1]/@href').extract(): ###
            #url = urljoin(response.url, link)
            self.cookie_num += 1
            yield Request(url, meta={'cookiejar': self.cookie_num},callback=self.parse_product)

        #To crawl next page.
        tmp = hxs.select('//div[@class="pageNumber"]//a[@class="arrow-right"]/@href').extract()
        if tmp:
            #url = urljoin(response.url, tmp[0])
            yield Request(tmp[0], callback=self.parse)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        tmp = hxs.select('//p[@class="pcode"]/span[@class="val"]/text()').extract()
        if tmp:
            loader.add_value('identifier', tmp[0].strip())
        else:
            log.msg('### No product ID at '+response.url, level=log.INFO)
            return
        tmp = hxs.select('//input[@name="productId"]/@value').extract()
        if tmp:
            loader.add_value('sku', tmp[0])
        name = ''
        tmp = hxs.select('//aside[@class="productDesc"]//span[@class="description"]/text()').extract()
        if tmp:
            name = tmp[0].strip()
            loader.add_value('name', name)
        else:
            log.msg('### No name at '+response.url, level=log.INFO)
        #price
        price = 0
        tmp = hxs.select('//aside[@class="productDesc"]//p[@itemprop="price"]/text()').extract()
        if tmp:
            price = extract_price(tmp[0].strip().replace(',',''))
            loader.add_value('price', price)
        #stock
        tmp = hxs.select('//button[@name="addToBagButton" and span="Add to bag"]')
        if tmp:
            loader.add_value('stock', 1)
        else:
            loader.add_value('stock', 0)
        #image_url
        tmp = hxs.select('//div[@class="productImage"]//img/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            loader.add_value('image_url', url)
        #brand
        loader.add_value('brand', 'Le Creuset')
        #category
        tmp = hxs.select('//nav[@id="breadcrumb"]/ul/li/a/text()').extract()
        if len(tmp)>1:
            for s in [s for s in tmp[1:]]:
                loader.add_value('category', s)
        #shipping_cost
        loader.add_value('shipping_cost', 4.95)


        product = loader.load_item()

        options = hxs.select('//fieldset[@class="att1"]/ul/li')
        if not options:
            if not product.get('identifier', None):
                log.msg('### No product ID at '+response.url, level=log.INFO)
            else:
                if not product['identifier'] in self.id_seen:
                    self.id_seen.append(product['identifier'])
                    yield product
                else:
                    log.msg('### Duplicate product ID at '+response.url, level=log.INFO)
            return
        #process options
        for sel in options: ###
            item = copy.deepcopy(product)
            tmp = sel.select('.//label/input/@value').extract()
            if tmp:
                item['identifier'] += '-' + tmp[0]
                item['name'] = name + ' - ' + tmp[0]

            if not item.get('identifier', None):
                log.msg('### No product ID at '+response.url, level=log.INFO)
            else:
                if not item['identifier'] in self.id_seen:
                    self.id_seen.append(item['identifier'])
                    yield item
                else:
                    log.msg('### Duplicate product ID at '+response.url, level=log.INFO)


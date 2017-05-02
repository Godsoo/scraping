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

class GoelectricalSpider(BaseSpider):
    name = 'lecreuset-goelectrical.co.uk'
    #download_delay = 3
    allowed_domains = ['go-electrical.co.uk']
    start_urls = ['http://www.go-electrical.co.uk/brands/le-creuset.html']
    #cookie_num = 0
    #brands = []
    id_seen = []

    def parse(self, response):
        #inspect_response(response, self)
        #yield Request('http://www.go-electrical.co.uk/brands/le-creuset/le-creuset-cast-iron-rectangular-dish-30cm.html', callback=self.parse_product)
        #return
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//div[contains(@class,"category-products")]//h2/a/@href').extract(): ###
            #url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_product)

        #To crawl next page.
        #return ###
        tmp = hxs.select('//a[@class="next"]/@href').extract()
        if tmp:
            #url = urljoin(response.url, tmp[0])
            yield Request(tmp[0], callback=self.parse)

    def parse_product(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        #Crawl options
        urls = hxs.select('//div[@id="available-product-options"]//a/@href').extract()
        if not response.meta.get('options', False) and urls:
            for url in urls:
                yield Request(url, meta={'options':True}, callback=self.parse_product)
            return

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        tmp = hxs.select('//meta[@itemprop="sku"]/@content').extract()
        if tmp:
            loader.add_value('identifier', tmp[0].strip())
            loader.add_value('sku', tmp[0])
        else:
            log.msg('### No product ID at '+response.url, level=log.INFO)
            return
        name = ''
        tmp = hxs.select('//meta[@itemprop="name"]/@content').extract()
        if tmp:
            name = tmp[0].strip()
            loader.add_value('name', name)
        else:
            log.msg('### No name at '+response.url, level=log.INFO)
        #price
        price = 0
        tmp = hxs.select('//meta[@itemprop="price"]/@content').extract()
        if tmp:
            price = extract_price(tmp[0].strip().replace(',',''))
            loader.add_value('price', price)
        #stock
        tmp = hxs.select('//meta[@itemprop="availability"]/@href').extract()
        if tmp and 'out' in tmp[0].lower():
            loader.add_value('stock', 0)
        else:
            loader.add_value('stock', 1)
        #image_url
        tmp = hxs.select('//div[@id="media_view"]/img/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            loader.add_value('image_url', url)
        #brand
        loader.add_value('brand', 'Le Creuset')
        #category
        tmp = hxs.select('//div[@class="breadcrumbs"]/ul/li/a/text()').extract()
        if len(tmp)>2:
            for s in tmp[2:]:
                loader.add_value('category', s)
        #shipping_cost
        #loader.add_value('shipping_cost', 4.95)

        product = loader.load_item()

        if not product['identifier'] in self.id_seen:
            self.id_seen.append(product['identifier'])
            yield product
        else:
            log.msg('### Duplicate product ID at '+response.url, level=log.INFO)


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

class RichmondcookshopSpider(BaseSpider):
    name = 'lecreuset-richmondcookshop.co.uk'
    #download_delay = 3
    allowed_domains = ['richmondcookshop.co.uk']
    start_urls = ['http://www.richmondcookshop.co.uk/']
    #cookie_num = 0
    #brands = []
    id_seen = []

    #GET http://www.richmondcookshop.co.uk/index.php?manufacturers_id=83
    def parse(self, response):
        #inspect_response(response, self)
        #yield Request('http://www.ecookshop.co.uk/ecookshop/product.asp?pid=962009161', callback=self.parse_product)
        #return
        hxs = HtmlXPathSelector(response)

        for key in hxs.select('//select[@name="manufacturers_id"]/option[contains(text(),"Le Creuset")]/@value').extract(): ###
            url = 'http://www.richmondcookshop.co.uk/index.php?manufacturers_id=%s' % key
            yield Request(url, callback=self.parse_products_list)

    def parse_products_list(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        links = hxs.select('//table[@class="productListing"]//td[@class="main"]/a[img]/@href').extract()
        for link in links: ###
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_product)

        #To crawl next page.
        #return ###
        tmp = hxs.select('//a[@class="pageResults" and contains(@title,"Next Page")]/@href').extract()
        if tmp:
            #url = urljoin(response.url, tmp[0])
            yield Request(tmp[0], callback=self.parse_products_list)

    def parse_product(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        tmp = hxs.select('//form[@name="cart_quantity"]//input[@name="products_id"]/@value').extract()
        if tmp:
            loader.add_value('identifier', tmp[0])
        else:
            log.msg('### No product ID at '+response.url, level=log.INFO)
            return
        tmp = hxs.select('//form[@name="cart_quantity"]//td[@class="main" and contains(text(),"MPN:")]/text()').extract()
        if tmp:
            loader.add_value('sku', tmp[0].replace('MPN:','').strip())
        name = ''
        tmp = hxs.select('//form[@name="cart_quantity"]//h1/text()').extract()
        if tmp:
            name = tmp[0].strip()
            loader.add_value('name', name)
        else:
            log.msg('### No name at '+response.url, level=log.INFO)
        #price
        price = 0
        tmp = hxs.select('//form[@name="cart_quantity"]//span[@class="productSpecialPrice"]/text()').extract()
        if tmp:
            price = extract_price(tmp[0].strip().replace(',',''))
            loader.add_value('price', price)
            loader.add_value('stock', 1)
        else:
            loader.add_value('stock', 0)
        #image_url
        tmp = hxs.select('//form[@name="cart_quantity"]//a[@rel="gallery"]/@href').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            loader.add_value('image_url', url)
        #brand
        loader.add_value('brand', 'Le Creuset')
        #category
        tmp = hxs.select('//a[@class="headerbreadcrumb"]/text()').extract()
        if len(tmp)>2:
            for s in tmp[1:-1]:
                loader.add_value('category', s)
        #shipping_cost
        if price<50:
            loader.add_value('shipping_cost', 4.99)

        product = loader.load_item()

        options = None
        #No options currently.
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
        #No options currently.
        for sel in options[0:1]: ###
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


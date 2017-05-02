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

class LoccitanedeSpider(BaseSpider):
    name = 'the-body-shop_loccitane_de'
    #download_delay = 1
    allowed_domains = ['loccitane.com']
    #start_urls = ['http://www.yves-rocher.co.uk/control/main/']
    start_urls = [
        'http://de.loccitane.com/fair-trade-karit%C3%A9butter,77,2,26106,238421.htm',
        'http://de.loccitane.com/karite-hand-creme,77,2,27689,238162.htm',
        'http://de.loccitane.com/verbene-duschgel,77,2,25882,383426.htm',
        'http://de.loccitane.com/eau-de-toilette-kirschbl%C3%BCte,77,2,25921,500581.htm#s=42623',
        'http://de.loccitane.com/verbene-eau-de-toilette,77,2,34187,383391.htm#s=42620',
        'http://de.loccitane.com/karit%C3%A9-lippenbalsam-rosenwonne,77,2,25851,618909.htm#s=42681',
        'http://de.loccitane.com/bb-cream-pr%C3%A9cieuse-lsf-30-heller-hauttyp,77,2,25863,691732.htm#s=61991',
        'http://de.loccitane.com/karit%C3%A9-leichte-gesichtscreme,77,2,25851,659383.htm#s=26066',
        'http://de.loccitane.com/immortelle-serum-pr%C3%A9cieux,77,2,25863,288457.htm#s=26066',
        'http://de.loccitane.com/cade-anti-aging-gesichtspflegekonzentrat,77,2,25900,274618.htm#s=26066',
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

        if not 'this.products = ' in response.body:
            log.msg('### Products data not found at '+response.url, level=log.INFO)
            return
        data = response.body.split('this.products = ',1)[1].split('(',1)[1].split(');',1)[0]
        j = json.loads(data)
        choice = 0
        if j[0]['sku']=='15GD075VB3':
            choice = 1
        price = 0
        stock = 0
        dd = j[choice]
        tmp = dd.get('productId', None)
        if tmp:
            loader.add_value('identifier', str(tmp))
            loader.add_value('sku', dd['sku'])
            price = extract_price(dd['price'].replace('.','').replace(',','.').strip())
            loader.add_value('price', price)
            loader.add_value('image_url', dd.get('productImageUrl', None))
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
        #price = 0
        #stock = 0
        #tmp = hxs.select('//div[@class="product-price"]/span[contains(@class,"price")]/text()').extract()
        #if tmp:
        #    price = extract_price(tmp[0].replace('.','').replace(',','.').strip())
        #    loader.add_value('price', price)
            #stock = 1
        #stock
        #stock = 0
        #tmp = hxs.select('//div[@id="col2"]//span[text()="In den Warenkorb"]')
        #if tmp:
        if price:
            stock = 1
        loader.add_value('stock', stock)
        #image_url
        #tmp = hxs.select('//img[@class="product"]/@src').extract()
        #if tmp:
        #    url = urljoin(response.url, tmp[0].strip())
        #    loader.add_value('image_url', url)
        #brand
        #tmp = hxs.select('//div[@class="primary-logo"]//img/@alt').extract()
        r = re.findall(r'"pageSectionTitle":.*?"(.+?)"', response.body)
        if r:
            loader.add_value('brand', r[0].decode('utf-8'))
        #category
        tmp = hxs.select('//div[@id="breadcrumb"]/ul/li/a/span/text()').extract()
        if len(tmp)>1:
            for s in tmp[1:]:
                loader.add_value('category', s)
        #shipping_cost
        if price<75:
            loader.add_value('shipping_cost', 5.50)
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


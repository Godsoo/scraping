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

class ThebodyshopdeSpider(BaseSpider):
    name = 'thebodyshop_de-thebodyshop_de'
    #download_delay = 1
    allowed_domains = ['thebodyshop.de']
    #start_urls = ['http://www.yves-rocher.co.uk/control/main/']
    start_urls = [
        'http://www.thebodyshop.de/angebote/kundenlieblinge/shea-body-butter.aspx',
        'http://www.thebodyshop.de/angebote/kundenlieblinge/hemp-hand-protector.aspx',
        'http://www.thebodyshop.de/unsere-serien/strawberry/strawberry-shower-gel.aspx',
        'http://www.thebodyshop.de/duefte/eau-de-toilette/white-musk-eau-de-toilette.aspx',
        'http://www.thebodyshop.de/duefte/voyage-collection/indian-night-jasmine-eau-de-toilette.aspx',
        'http://www.thebodyshop.de/make-up/lippen/colour-crush-red-lipsticks.aspx',
        'http://www.thebodyshop.de/make-up/all-in-one/all-in-one-bb-cream.aspx',
        'http://www.thebodyshop.de/bestseller/gesichtspflege/vitamin-e-moisture-cream.aspx',
        'http://www.thebodyshop.de/gesichtspflege/serum/drops-of-youth-concentrate.aspx',
        'http://www.thebodyshop.de/gesichtspflege/pflege-fuer-maenner/for-men-maca-root-energetic-face-protector.aspx',
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

        choice = None
        tmp = hxs.select('//ul[@class="size-selector"]//input/@name').extract()
        if tmp:
            if 'Shea Body Butter' in tmp[0]:
                choice = '200#ml'
            elif 'Hemp Hand Protector' in tmp[0]:
                choice = '100#ml'
            elif 'White Musk' in tmp[0]:
                choice = '60#ml'
        price = 0
        stock = 0
        tmp = None
        if choice:
            tmp = hxs.select('//ul[@class="size-selector"]//label[contains(@data-weight,"{}")]/@data-weight'.format(choice)).extract()
        if tmp:
            dd = tmp[0].split()[0].split('#')
            loader.add_value('identifier', dd[4])
            loader.add_value('sku', dd[4])
            price = extract_price(dd[5].replace('.','').replace(',','.').strip())
            loader.add_value('price', price)
        else:
            r = re.findall(r'variantID = "([\d.]+)"', response.body)
            if r:
                loader.add_value('identifier', r[0])
                loader.add_value('sku', r[0])
                r = re.findall(r'unitPrice = "([\d.]+)"', response.body)
                if r:
                    price = extract_price(r[0].replace(',','').strip())
                    loader.add_value('price', price)
            else:
                log.msg('### No product ID at '+response.url, level=log.INFO)
                return
        #tmp = hxs.select('//input[@name="productId"]/@value').extract()
        #if tmp:
        #    loader.add_value('sku', tmp[0])
        name = ''
        tmp = hxs.select('//h1[@class="title"]/@title').extract()
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
        tmp = hxs.select('//img[@class="product"]/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0].strip())
            loader.add_value('image_url', url)
        #brand
        #tmp = hxs.select('//div[@class="primary-logo"]//img/@alt').extract()
        #if tmp:
        #    loader.add_value('brand', tmp[0].upper())
        loader.add_value('brand', 'THE BODY SHOP')
        #category
        tmp = hxs.select('//nav[@id="breadcrumb_product"]/ul/li/a/text()').extract()
        if len(tmp)>1:
            for s in tmp[1:]:
                loader.add_value('category', s)
        #shipping_cost
        if price<40:
            loader.add_value('shipping_cost', 5.00)
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


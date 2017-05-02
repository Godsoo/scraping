import re
import os
from decimal import Decimal

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

class WestelmSpider(BaseSpider):
    name = 'westelm.co.uk'
    # download_delay = 1
    allowed_domains = ['westelm.co.uk']
    start_urls = ['http://www.westelm.co.uk']
    # cookie_num = 0
    # brands = []

    def parse(self, response):
        # inspect_response(response, self)
        # yield Request('http://www.westelm.co.uk/solid-rugs-we-uk', callback=self.parse_products_list)
        # yield Request('http://www.westelm.co.uk/everett-upholstered-sofa-g994-uk', meta={'categories':['1', '2']}, callback=self.parse_product)
        # return
        hxs = HtmlXPathSelector(response)
        # self.brands = hxs.select('//ul[@id="nav"]/li[contains(@class,"brands")]/ul//li[contains(@class,"level2")]/a/span/text()').extract()
        for link in hxs.select('//ul[@class="nav"]/li/div//ul/li/a[not(starts-with(@href,"/all-"))]/@href').extract():  # ##
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_products_list)

    def parse_products_list(self, response):
        # inspect_response(response, self)
        # return
        hxs = HtmlXPathSelector(response)
        category = ''
        tmp = hxs.select('//div[@class="supercategory-title"]/text()').extract()
        if tmp:
            category = tmp[0].strip()
        subcategory = ''
        tmp = hxs.select('//ul[@class="category-list"]/li/a/strong/text()').extract()
        if tmp:
            subcategory = tmp[0].strip()

        # links = hxs.select('//div[@class="col-3 first lt-nav"]//li/a/@href').extract()
        # if links:
        #    #Crawl subcategories.
        #    for link in links: ###
        #        url = urljoin(response.url, link)
        #        yield Request(url, callback=self.parse_products_list)
        #    return

        # inspect_response(response, self)
        # return
        # Crawl product list.
        for link in hxs.select('//div[@id="item-list"]/div[@class="row-fluid"]/div//h5/a/@href').extract():  # ##
            url = urljoin(response.url, link)
            yield Request(url, meta={'categories':[category, subcategory]}, callback=self.parse_product)

        # To crawl next page.
        #return ###
        tmp = hxs.select('//ul[contains(@class,"pagination-links ")]/li/a[@rel="next"]/@href').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            yield Request(url, callback=self.parse_products_list)

    def parse_product(self, response):
        # inspect_response(response, self)
        # return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        tmp = hxs.select('//h1[@itemprop="name"]/text()').extract()
        if tmp:
            loader.add_value('name', tmp[0].strip())
        for s in response.meta['categories']:
            loader.add_value('category', s)

        sku = response.url.split('-')[-1]
        loader.add_value('sku', sku)

        product = loader.load_item()

        tmp = hxs.select('//meta[@itemprop="sku"]/@content').extract()
        if '/product/' in response.url:
            url = 'http://www.westelm.co.uk/api/items?fieldset=details&language=en&country=US&currency=GBP&pricelevel=5&custitem_is_preview_item_uk=F&id=%s' % response.url.split('/product/')[-1]
            yield Request(url, meta={'product':product}, callback=self.parse_id)
        elif tmp:
            url = 'http://www.westelm.co.uk/api/items?fieldset=details&language=en&country=US&currency=GBP&pricelevel=5&custitem_is_preview_item_uk=F&url=%s' % tmp[0]
            yield Request(url, meta={'product':product}, callback=self.parse_id)
        else:
            log.msg('Product SKU was not found at ' + response.url)
        #    item = copy.deepcopy(product)

    # http://www.westelm.co.uk/api/items?fieldset=details&language=en&country=US&currency=GBP&pricelevel=5&custitem_is_preview_item_uk=F&url=elton-settee-g235-uk
    # http://www.westelm.co.uk/api/items?fieldset=details&language=en&country=US&currency=GBP&pricelevel=5&custitem_is_preview_item_uk=F&id=238903
    def parse_id(self, response):
        # inspect_response(response, self)
        # return
        product = response.meta['product']
        j = json.loads(response.body)
        pid = j['items'][0].get('internalid', None)
        if pid:
            product['identifier'] = str(pid)
            if not product.get('name', None):
                product['name'] = j['items'][0].get('displayname', '')
            # product['image_url'] = j['items'][0].get('custitem_ecom_sku_member_image_url','')
            tmp = j['items'][0].get('custitem_alt_img_zoom_1_url', '')
            if not tmp:
                tmp = j['items'][0].get('custitem_ecom_sku_member_image_url', '')
            if tmp:
                product['image_url'] = urljoin(response.url, tmp)
            price = extract_price(str(j['items'][0].get('onlinecustomerprice', 0)))
            product['price'] = price
            if price:
                if Decimal(price) < 150.0:
                    product['shipping_cost'] = '8.00'
                elif 150.0 <= Decimal(price) < 300.0:
                    product['shipping_cost'] = '15.0'
                elif 300.0 <= Decimal(price) < 600.0:
                    product['shipping_cost'] = '29.0'
                elif 600.0 <= Decimal(price) < 900.0:
                    product['shipping_cost'] = '39.0'
                elif 900.0 <= Decimal(price) < 1200.0:
                    product['shipping_cost'] = '49.0'
                elif 1200.0 < Decimal(price):
                    product['shipping_cost'] = '59.0'

            if j['items'][0].get('isinstock', False):
                product['stock'] = 1
            else:
                product['stock'] = 0
            url = 'http://www.westelm.co.uk/CustomWE-UK/services/shopping/skuSelection.ss?groupId=%s' % str(pid)
            return Request(url, meta={'product':product}, callback=self.parse_skus)
        else:
            log.msg('Product ID was not found at ' + product['url'], level=log.INFO)

    # http://www.westelm.co.uk/CustomWE-UK/services/shopping/skuSelection.ss?groupId=130301
    def parse_skus(self, response):
        # inspect_response(response, self)
        # return
        product = response.meta['product']
        j = json.loads(response.body)
        if j and j[0]['results']:
            for j1 in j[0]['results']:  # ##
                item = copy.deepcopy(product)
                item['identifier'] += '-' + str(j1.get('internalid', ''))
                # item['name'] = j1.get('sku_web_title','')
                attrs = sorted([k for k in j1.keys() if k.startswith('attribute_')])
                ss = [j1[attr] for attr in attrs if j1[attr]]
                if ss:
                    item['name'] += ' - ' + '-'.join(ss)
                tmp = j1.get('custitem_ecom_sku_member_image_url', '')
                if tmp:
                    item['image_url'] = urljoin(response.url, tmp)
                price = extract_price(j1.get('sku_price', ''))
                if j1.get('sku_special_price', ''):
                    price = extract_price(j1.get('sku_special_price', ''))
                item['price'] = price
                if price:
                    if Decimal(price) < 150.0:
                        product['shipping_cost'] = '8.00'
                    elif 150.0 <= Decimal(price) < 300.0:
                        product['shipping_cost'] = '15.0'
                    elif 300.0 <= Decimal(price) < 600.0:
                        product['shipping_cost'] = '29.0'
                    elif 600.0 <= Decimal(price) < 900.0:
                        product['shipping_cost'] = '39.0'
                    elif 900.0 <= Decimal(price) < 1200.0:
                        product['shipping_cost'] = '49.0'
                    elif 1200.0 < Decimal(price):
                        product['shipping_cost'] = '59.0'
                if j1.get('isinstock', False):
                    item['stock'] = 1
                else:
                    item['stock'] = 0

                yield item
        else:
            yield product


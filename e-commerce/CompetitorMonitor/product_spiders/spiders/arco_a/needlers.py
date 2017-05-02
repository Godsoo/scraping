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

class NeedlersSpider(BaseSpider):
    name = 'arco-a-needlers.co.uk'
    allowed_domains = ['needlers.co.uk']
    start_urls = ['http://www.needlers.co.uk']
    brands = []

    def parse(self, response):
        # inspect_response(response, self)
        # yield Request('http://www.needlers.co.uk/work-clothing/casual-wear/sweatshirts/kestrel-deluxe-sweatshirt-navy-large.html', meta={'item':{}}, callback=self.parse_product)
        # return
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//nav[@id="site-nav"]/ul/li/ul/li/a/@href').extract():  # ##
            yield Request(url, callback=self.parse_products_list)

    # var settings = { categoryId: 292, baseUrl: "http://www.needlers.co.uk/" }
    # http://www.needlers.co.uk/ajax/category/getproducts/?categoryid=10
    def parse_products_list(self, response):
        # inspect_response(response, self)
        # return
        # hxs = HtmlXPathSelector(response)
        if 'categoryId:' in response.body:
            id = response.body.split('categoryId:', 1)[1].split(',', 1)[0].strip()
            url = 'http://www.needlers.co.uk/ajax/category/getproducts/?categoryid=%s' % id
            yield Request(url, callback=self.parse_products_json)
        else:
            log.msg('### Category ID was not found at ' + response.url, level=log.INFO)

    def parse_products_json(self, response):
        # inspect_response(response, self)
        # return
        j = json.loads(response.body)
        for d in j['products']:  # ##
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('url', d['url'])
            loader.add_value('identifier', d['sku'])
            loader.add_value('name', d['name'])
            price = extract_price(d['price'])
            loader.add_value('price', price)
            loader.add_value('image_url', d['image'])
            tmp = d.get('categories', None)
            if tmp:
                tmp = [dd['name'] for dd in j['categories'] if dd['id'] == tmp[0]]
                if tmp:
                    loader.add_value('category', tmp[0])
            if d['price']:
                loader.add_value('stock', 1)
            else:
                loader.add_value('stock', 0)

            yield Request(d['url'], meta={'item':loader.load_item()}, callback=self.parse_product)

    def parse_product(self, response):
        # inspect_response(response, self)
        # return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        tmp = hxs.select('//div[@class="breadcrumbs"]/ul/li[contains(@class,"category")]/a/text()').extract()
        if tmp:
            for s in tmp:
                loader.add_value('category', s)
        p = loader.load_item()
        product = response.meta['item']
        product['category'] = p['category']
        identifier = product['identifier']
        tmp = hxs.select('//div[@class="breadcrumbs"]/ul/li[@class="product"]/strong/text()').extract()
        if tmp:
            product['name'] = tmp[0]
        name = product['name']

        price = hxs.select('//div[@class="price"]/span/text()').extract()
        if not product['price'] and price:
            product['price'] = extract_price(price[0])

        options = hxs.select('//select[@id="simple-selection"]/option[not(@value="null")]')
        if not options:
            tmp = hxs.select('//div[@id="product-options"]//input[@id="sku-code"]/@value').extract()
            if tmp:
                product['sku'] = tmp[0]
            tmp = hxs.select('//form[@id="product_addtocart_form"]/@action').extract()
            if tmp and '/product/' in tmp[0]:
                product['identifier'] = tmp[0].split('/product/', 1)[1].split('/', 1)[0]
            yield product
            return
        for sel in options:  # ##
            item = copy.deepcopy(product)
            tmp = sel.select('text()').extract()
            if tmp:
                item['name'] = name + ' - ' + tmp[0]
            tmp = sel.select('@data-sku').extract()
            if tmp:
                item['identifier'] = identifier + '-' + tmp[0]
                item['sku'] = tmp[0]
            tmp = sel.select('@value').extract()
            if tmp:
                item['identifier'] = tmp[0]
            tmp = sel.select('@data-simple-price').extract()
            if tmp:
                price = round(extract_price(tmp[0]), 2)
                item['price'] = price

            yield item


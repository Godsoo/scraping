import re
import os

from product_spiders.base_spiders.primary_spider import PrimarySpider
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

import itertools

HERE = os.path.abspath(os.path.dirname(__file__))


class TowersuppliesSpider(PrimarySpider):
    name = 'arco-a-towersupplies.com'
    allowed_domains = ['towersupplies.com']
    start_urls = ['http://www.towersupplies.com']

    brands = []
    cookie_num = 0

    csv_file = 'towersupplies_crawl.csv'

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for link in hxs.select('//*[@class="meganav"]//a/@href').extract():
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        links = hxs.select('//div[@id="page"]/div/ul/li/a[contains(@href,"/category/")]/@href').extract()
        if links:
            # sub-categories page
            for link in links:
                url = urljoin(response.url, link)
                yield Request(url, callback=self.parse_products_list)
            return

        category = ''
        tmp = hxs.select('//div[@class="breadcrumb"]//li/a/text()').extract()
        if len(tmp) > 2:
            category = tmp[-1].strip()
        for link in hxs.select('//div[@id="page"]/div/ul/li/a[contains(@href,"/product/")]/@href').extract():  # ##
            url = urljoin(response.url, link)
            yield Request(url, meta={'category':category}, callback=self.parse_product)

        tmp = hxs.select('//p[contains(@class,"pagination")][1]/a[contains(text(),"Next Page")]/@href').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            yield Request(url, callback=self.parse_products_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        loader.add_value('category', response.meta['category'])
        code = ''
        tmp = hxs.select('//h1[@itemprop="name"]/following-sibling::span[@class="code"]/text()').extract()
        if tmp:
            code = tmp[0]
            loader.add_value('sku', code)
        name = ''
        tmp = hxs.select('//h1[@itemprop="name"]/text()').extract()
        if tmp:
            name = tmp[0].strip()
            if code:
                name = code + ' ' + name
            loader.add_value('name', name)
        tmp = hxs.select('//div[contains(@class,"gallery")]//img[@class="etalage_source_image"]/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            loader.add_value('image_url', url)
        tmp = hxs.select('//input[@name="product_id"]/@value').extract()
        if tmp:
            loader.add_value('identifier', tmp[0])
        tmp = hxs.select('//div[@itemprop="price"]/text()').extract()
        if not tmp:
            tmp = hxs.select('//div[@id="prices"]/text()').extract()
        if tmp:
            price = extract_price(tmp[0].strip())
            loader.add_value('price', price)
            loader.add_value('stock', 1)
        else:
            loader.add_value('stock', 0)

        product = loader.load_item()

        url_post = response.url

        selections = hxs.select('//select[@class="select"]')
        if not selections:
            if product.get('identifier', None):
                yield product
            return

        attrs = []
        for sel in selections:
            attr_name = ''
            tmp = sel.select('@name').extract()
            if tmp:
                attr_name = tmp[0]
            attr_values = []
            for option in sel.select('option'):
                value = ''
                tmp = option.select('@value').extract()
                if tmp:
                    value = tmp[0]
                txt = ''
                tmp = option.select('text()').extract()
                if tmp:
                    txt = tmp[0].strip()
                if value != '':
                    attr_values.append((attr_name, value, txt))
            attrs.append(attr_values)

        for option in itertools.product(*attrs):
            item = copy.deepcopy(product)
            item['name'] += ' - ' + '-'.join([attr[2] for attr in option])
            item['identifier'] += '-' + '-'.join([attr[1] for attr in option])

            formdata = {}
            for attr in option:
                formdata[attr[0]] = attr[1]

            yield FormRequest(response.url, formdata=formdata, meta={'item':item}, dont_filter=True, callback=self.parse_stock)

    def parse_stock(self, response):
        item = response.meta['item']
        hxs = HtmlXPathSelector(response)

        tmp = hxs.select('//div[contains(@class,"gallery")]//img[@class="etalage_source_image"]/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            item['image_url'] = url
        tmp = hxs.select('//div[@itemprop="price"]/text()').extract()
        if not tmp:
            tmp = hxs.select('//div[@id="prices"]/text()').extract()
        if tmp:
            price = extract_price(tmp[0].strip())
            item['price'] = price
            item['stock'] = 1
        else:
            item['stock'] = 0

        return item

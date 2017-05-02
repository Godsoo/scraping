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

class CellbikesSpider(BaseSpider):
    name = 'cellbikes.com.au'
    # download_delay = 1
    allowed_domains = ['cellbikes.com.au']
    # start_urls = ['http://www.cellbikes.com.au/']
    start_urls = ['http://www.cellbikes.com.au/c.980629/ShopFlow/sc.environment.ssp?v=4&lang=en_AU&cur=AUD']
    brands = []

    # Multiple options
    # http://www.cellbikes.com.au/Santini-H2O-Winter-Booties
    # GET options json
    # http://www.cellbikes.com.au/api/items?include=facets&fieldset=details&language=en&country=AU&currency=AUD&pricelevel=5&c=980629&n=3&url=Santini-H2O-Winter-Booties
    # http://www.cellbikes.com.au/api/items?include=facets&fieldset=details&language=en&country=AU&currency=AUD&pricelevel=5&c=980629&n=3&id=18593
    # <meta itemprop="url" content="/Santini-H2O-Winter-Booties"/>

    def parse(self, response):
        # inspect_response(response, self)
        # return
        if 'SC.ENVIRONMENT.CATEGORIES = {' in response.body:
            data = '{' + response.body.split('SC.ENVIRONMENT.CATEGORIES = {', 1)[1].split('};', 1)[0] + '}'
            j = json.loads(data)
            self.brands = [d['itemid'] for d in j['brands']['categories'].values()]

        yield Request('http://www.cellbikes.com.au/', callback=self.parse_home)

    def parse_home(self, response):
        # inspect_response(response, self)
        # yield Request('http://www.cellbikes.com.au/Bikes/BEST_Fixies_UNDER_500?order=custitem_best_selling:desc&page=2', callback=self.parse_products_list)
        # yield Request('http://www.cellbikes.com.au/Santini-H2O-Winter-Booties', callback=self.parse_product)
        # yield Request('http://www.cellbikes.com.au/Castelli-Rosso-Corsa-6in-Sock', callback=self.parse_product)
        # return
        hxs = HtmlXPathSelector(response)
        tmp = hxs.select('//ul[@class="nav"]/li[last()]/ul//a/text()').extract()
        if tmp:
            self.brands = [s.strip() for s in tmp[:-1]] + self.brands
        for link in hxs.select('//ul[@class="nav"]/li[position()<last()]/ul/li/ul/li/a/@href').extract():  # ##
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_products_list)
        # Miss url
        #return ###
        urls = [
                'http://www.cellbikes.com.au/Bikes/bike-specials-road-bike-mountain-bike-city-bike',
                'http://www.cellbikes.com.au/Specials/LAST-Chance-Winter-Clothing',
        ]
        for url in urls:  # ##
            yield Request(url, callback=self.parse_products_list)


    def parse_products_list(self, response):
        # inspect_response(response, self)
        # return
        hxs = HtmlXPathSelector(response)
        for link in hxs.select('//h2/a/@href').extract():  # ##
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_product)

        # To crawl next page.
        #return ###
        tmp = hxs.select('//link[@rel="next"]/@href').extract()
        if tmp:
            yield Request(tmp[0], callback=self.parse_products_list)

    def parse_product(self, response):
        # inspect_response(response, self)
        # return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        tmp = hxs.select('//p[@class="sku-number"]/span/text()').extract()
        if tmp:
            loader.add_value('identifier', tmp[0])
            loader.add_value('sku', tmp[0])
        else:
            log.msg('### No product ID at ' + response.url, level=log.INFO)
        name = ''
        tmp = hxs.select('//h1[@itemprop="name"]/text()').extract()
        if tmp:
            name = tmp[0].strip()
            loader.add_value('name', tmp[0].strip())
        else:
            log.msg('### No name at ' + response.url, level=log.INFO)
        # price
        price = 0
        tmp = hxs.select('//strong[@itemprop="price"]/text()').extract()
        if tmp:
            price = extract_price(tmp[0].strip())
            loader.add_value('price', price)
        # image_url
        tmp = hxs.select('//img[@itemprop="image"]/@src').extract()
        if tmp:
            loader.add_value('image_url', tmp[0])
        # brand
        for brand in self.brands:
            if brand.lower() in name.lower():
                loader.add_value('brand', brand)
                break
        # category
        tmp = hxs.select('//ul[@itemprop="breadcrumb"]/li/a/text()').extract()
        if len(tmp):
            tmp = tmp[1:]
        if len(tmp) > 3:
            tmp = tmp[-3:]
        for s in tmp:
            loader.add_value('category', s)
        # shipping_cost
        shipping_cost = '9.90'

        # stock
        if not price:
            loader.add_value('stock', 0)
        else:
            tmp = hxs.select('//span[contains(@class,"stock-status")]/text()').extract()
            if tmp and 'Out' in tmp[0]:
                loader.add_value('stock', 0)
            else:
                loader.add_value('stock', 1)

        product = loader.load_item()
        # options = hxs.select('//ul[contains(@id,"option-custcol")]/li/a').extract()
        # if not options:
        #    yield product
        #    return
        tmp = hxs.select('//meta[@itemprop="url"]/@content').extract()
        if product['price']<=99:
            product['shipping_cost'] = shipping_cost

        if not tmp:
            yield product
            return
        else:
            # process options
            if tmp[0].startswith('/'):
                tmp[0] = tmp[0][1:]
            if tmp[0].startswith('product/'):
                tmp[0] = tmp[0][8:]
                url = 'http://www.cellbikes.com.au/api/items?include=facets&fieldset=details&language=en&country=AU&currency=AUD&pricelevel=5&c=980629&n=3&id=%s' % tmp[0]
            else:
                url = 'http://www.cellbikes.com.au/api/items?include=facets&fieldset=details&language=en&country=AU&currency=AUD&pricelevel=5&c=980629&n=3&url=%s' % tmp[0]
            yield Request(url, meta={'product':product}, callback=self.parse_options)

    def parse_options(self, response):
        # inspect_response(response, self)
        # return
        product = response.meta['product']
        j = json.loads(response.body)
        if not j['items']:
            yield product
            return
        fields = [d.get('sourcefrom', '') for d in j['items'][0]['itemoptions_detail']['fields']]
        fields = [d for d in fields if d]
        if not fields:
            yield product
            return
        # process options
        for d in j['items'][0]['matrixchilditems_detail']:  # ##
            item = copy.deepcopy(product)
            item['identifier'] = d['internalid']
            # item['sku'] = d['internalid']
            # item['name'] = d['itemid']
            keys = [re.search(r'custitem\d+', k).string for k in d.keys() if re.search(r'custitem\d+', k)]
            if keys:
                item['name'] += ' - ' + '-'.join([str(d[k]) for k in keys])
            if not item.get('brand', None):
                for brand in self.brands:
                    if brand.lower() in d['itemid'].lower():
                        item['brand'] = brand
                        break

            price = extract_price(str(d['onlinecustomerprice_detail']['onlinecustomerprice']))
            item['price'] = price

            if item['price']<=99:
                item['shipping_cost'] = '9.90'

            if d["showoutofstockmessage"]:
                item['stock'] = 0
            else:
                item['stock'] = 1
            yield item

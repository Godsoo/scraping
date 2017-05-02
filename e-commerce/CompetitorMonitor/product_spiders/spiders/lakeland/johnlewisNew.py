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

from product_spiders.base_spiders import PrimarySpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from scrapy import log
from scrapy.shell import inspect_response

from urlparse import urljoin

import itertools
import json
import copy
import lxml

from scrapy.item import Item, Field

HERE = os.path.abspath(os.path.dirname(__file__))

class YMeta(Item):
    promotions = Field()

class JohnlewisNewSpider(PrimarySpider):
    name = 'johnlewis'
    #download_delay = 3
    allowed_domains = ['johnlewis.com']
    start_urls = ['http://www.johnlewis.com/']

    csv_file = 'lakeland_johnlewis_new_as_prim.csv'

    #cookie_num = 0
    #brands = []
    id_seen = []

    def parse(self, response):
        #inspect_response(response, self)
        #yield Request('http://www.johnlewis.com/browse/home-garden/bathroom/showers-shower-heads/_/N-5ub9', callback=self.parse_products_list)
        #yield Request('http://www.johnlewis.com/ghd-eclipse-hair-styler-with-free-paddle-brush-heat-protect-spray/p234538859?navAction=jump', callback=self.parse_product)
        #return
        hxs = HtmlXPathSelector(response)
        links = [
            'http://www.johnlewis.com/home-garden/bathroom/c6000073?rdr=1',
            'http://www.johnlewis.com/home-garden/kitchen/c60000557?rdr=1',
            'http://www.johnlewis.com/home-garden/utility-room/c6000054?rdr=1',
            'http://www.johnlewis.com/electricals/cookers-ovens/c6000046?rdr=1',
        ]
        for link in hxs.select('//strong[contains(text(),"Cooking & Dining")]/following::ul[1]/li/a/@href').extract():
            links.append(link)
        for link in hxs.select('//strong[contains(text(),"Small Appliances")]/following::ul[1]/li/a/@href').extract():
            links.append(link)
        for link in hxs.select('//strong[contains(text(),"Gift Food")]/following::ul[1]/li/a/@href').extract():
            links.append(link)
        for link in hxs.select('//strong[contains(text(),"Alcohol Gifts")]/following::ul[1]/li/a/@href').extract():
            links.append(link)

        for link in links: ###
            url = urljoin(response.url, link)
            if '/browse/' in url:
                yield Request(url, callback=self.parse_products_list)
            else:
                yield Request(url, callback=self.parse_category)

    def parse_category(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)
        url_start = '/'.join(response.url.split('/')[:-1])
        for link in hxs.select('//div[contains(@class,"lt-nav")]//a/@href').extract(): ###
            url = urljoin(response.url, link)
            if url.startswith(url_start):
                #print '!!! sub-category', url
                yield Request(url, callback=self.parse_category)
            elif '/browse/' in url:
                #print '!!! products listing', url
                yield Request(url, callback=self.parse_products_list)

    def parse_products_list(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        links = hxs.select('//div[@class="products"]//article/a/@href').extract()
        for link in links: ###
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_product)

        #To crawl next page.
        #return ###
        tmp = hxs.select('//div[@class="pagination"]//li[@class="next"]/a/@href').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            yield Request(url, callback=self.parse_products_list)

    def parse_product(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)
        colours = hxs.select('//div[contains(@class,"mod-product-colour")]//a/@href').extract()
        for url in colours:
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        tmp = hxs.select('//div[@id="prod-product-code"]/p/text()').extract()
        if not tmp:
            tmp = hxs.select('//div[@itemprop="offers"]//span[contains(text(),"Product code :")]/strong/text()').extract()
        if not tmp:
            tmp = hxs.select('//div[@itemprop="offers"]//h4[contains(text(),"Product code :")]/../p/text()').extract()
        if tmp:
            loader.add_value('identifier', tmp[0])
        else:
            #log.msg('### No product ID at '+response.url, level=log.INFO)
            #return
            pass
        tmp = hxs.select('//input[@name="/atg/store/order/purchase/CartFormHandler.productId"]/@value').extract()
        if tmp:
            loader.add_value('sku', tmp[0])
        name = ''
        tmp = hxs.select('//h1[@id="prod-title"]//text()').extract()
        if not tmp:
            tmp = hxs.select('//h1/span/text()').extract()
        if tmp:
            name = ' '.join(tmp).strip()
            loader.add_value('name', name)
        else:
            log.msg('### No name at '+response.url, level=log.INFO)
        #price
        price = 0
        stock = 0
        tmp = hxs.select('//span[@itemprop="price"]/text()').extract()
        if not tmp:
            tmp = hxs.select('//div[@class="basket-fields"]//strong[@class="price"]/text()').extract()
        if tmp:
            price = extract_price(tmp[0].strip().replace(',',''))
            stock = 1
        loader.add_value('price', price)
        #stock
        tmp = hxs.select('//form[@id="save-product-to-cart"]//p[not(contains(@class,"hidden"))]/strong[text()="Out of stock"]')
        if tmp:
            stock = 0
        loader.add_value('stock', stock)
        #image_url
        tmp = hxs.select('//img[@itemprop="image"]/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            loader.add_value('image_url', url)
        #brand
        tmp = hxs.select('//div[@itemprop="brand"]/span/text()').extract()
        if tmp:
            loader.add_value('brand', tmp[0].strip())
        #category
        tmp = hxs.select('//div[@id="breadcrumbs"]/ol/li/a/text()').extract()
        if len(tmp)>1:
            for s in tmp[1:]:
                loader.add_value('category', s)
        #shipping_cost
        if price<50:
            loader.add_value('shipping_cost', 3.00)

        product = loader.load_item()

        metadata = YMeta()
        tmp = hxs.select('//ul[@class="expand-wrapper"]/li/text()').extract()
        if tmp:
            if 'REDUCED TO CLEAR' in tmp[0].upper() or 'ONLINE EXCLUSIVE SPECIAL' in tmp[0].upper():
                metadata['promotions'] = tmp[0]
        product['metadata'] = metadata

        options = hxs.select('//div[not(contains(@class,"mod-product-colour"))]/div/ul[contains(@class, "selection-grid")]/li')
        #process options
        if options:
            for sel in options: ###
                item = copy.deepcopy(product)
                tmp = sel.select('@data-jl-product-code').extract()
                if tmp:
                    item['identifier'] = tmp[0]
                tmp = sel.select('a/img/@alt').extract()
                if not tmp:
                    tmp = sel.select('a/span/text()').extract()
                if tmp:
                    item['name'] = name + ' - ' + tmp[0]
                tmp = sel.select('@data-jl-stock').extract()
                if tmp and tmp[0] == '0':
                    item['stock'] = 0
                else:
                    item['stock'] = 1
                tmp = sel.select('@data-jl-price').extract()
                if tmp:
                    price = extract_price(tmp[0].strip().replace(',',''))
                    item['price'] = price
                    if price<50:
                        item['shipping_cost'] = 3.00

                if not item.get('identifier', None):
                    log.msg('### No product ID at '+response.url, level=log.INFO)
                else:
                    if not item['identifier'] in self.id_seen:
                        self.id_seen.append(item['identifier'])
                        yield item
                    else:
                        log.msg('### Duplicate product ID at '+response.url, level=log.INFO)
            return
        #http://www.johnlewis.com/missprint-garden-city-table-linen-accessories/p89014118
        options = hxs.select('//section[@id="grid-wrapper"]//form') or hxs.select('//div[@id="prod-multi-product-types"]//div[@itemprop="offers"]')
        if options:
            for option in options: ###
                productn = copy.deepcopy(product)
                tmp = option.select('.//p[@class="product-code"]/strong/text()').extract() or option.select('.//h4[contains(text(), "Product code")]/../p/text()').extract()
                if tmp:
                    productn['identifier'] = tmp[0].strip()
                name =''
                tmp = option.select('.//h3/a/text()').extract()
                if tmp:
                    name = tmp[0]
                    productn['name'] = tmp[0]
                else:
                    productn['name'] = product['name'] + ' ' + option.select('.//h3/text()').extract()[0]
                tmp = option.select('.//@data-jl-stock').extract()
                if tmp and tmp[0] == '0':
                    productn['stock'] = 0
                else:
                    productn['stock'] = 1
                tmp = option.select('.//strong[@class="price"]/text()').extract() or option.select('.//p[@class="price"]/strong/text()').extract()
                if tmp:
                    price = extract_price(tmp[0].strip().replace(',',''))
                    productn['price'] = price
                    if price<50:
                        productn['shipping_cost'] = 3.00
                sels = option.select('.//option[@data-jl-product-code]')
                if sels:
                    for sel in sels: ###
                        item = copy.deepcopy(productn)
                        tmp = sel.select('@data-jl-product-code').extract()
                        if tmp:
                            item['identifier'] = tmp[0]
                        tmp = sel.select('text()').extract()
                        if tmp:
                            item['name'] = name + ' - ' + tmp[0].split(',',1)[0].strip()
                        else:
                            item['name'] = name
                        tmp = sel.select('@data-jl-stock').extract()
                        if tmp and tmp[0] == '0':
                            item['stock'] = 0
                        else:
                            item['stock'] = 1
                        tmp = sel.select('@data-jl-price').extract()
                        if tmp:
                            price = extract_price(tmp[0].strip().replace(',',''))
                            item['price'] = price
                            if price<50:
                                item['shipping_cost'] = 3.00

                        if not item.get('identifier', None):
                            log.msg('### No product ID at '+response.url, level=log.INFO)
                        else:
                            if not item['identifier'] in self.id_seen:
                                self.id_seen.append(item['identifier'])
                                yield item
                            else:
                                log.msg('### Duplicate product ID at '+response.url, level=log.INFO)
                #return
                else:
                    if not productn.get('identifier', None):
                        log.msg('### No product ID at '+response.url, level=log.INFO)
                    else:
                        if not productn['identifier'] in self.id_seen:
                            self.id_seen.append(productn['identifier'])
                            yield productn
                        else:
                            log.msg('### Duplicate product ID at '+response.url, level=log.INFO)
            return

        #no options
        if not product.get('identifier', None):
            log.msg('### No product ID at '+response.url, level=log.INFO)
        else:
            if not product['identifier'] in self.id_seen:
                self.id_seen.append(product['identifier'])
                yield product
            else:
                log.msg('### Duplicate product ID at '+response.url, level=log.INFO)



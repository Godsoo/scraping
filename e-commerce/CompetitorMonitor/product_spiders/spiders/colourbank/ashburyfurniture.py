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

class AshburyfurnitureSpider(BaseSpider):
    name = 'ashburyfurniture'
    #download_delay = 1
    allowed_domains = ['ashburyfurniture.co.uk']
    start_urls = ['https://ashburyfurniture.co.uk/a-z/']
    #cookie_num = 0
    #brands = []
    id_seen = []

    def parse(self, response):
        #inspect_response(response, self)
        #yield Request('https://ashburyfurniture.co.uk/product/parker-knoll-westbury-grand-sofa/', meta={'brand':'test'}, callback=self.parse_product)
        #return
        hxs = HtmlXPathSelector(response)

        for link in hxs.select('//ul[@id="index"]//a/@href').extract(): ###
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_products_list)

    def parse_products_list(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        #Crawl product list
        for sel in hxs.select('//article'): ###
            brand = None
            tmp = sel.select('.//img[@class="product-card_logo"]/@alt').extract()
            if tmp:
                brand = tmp[0]
            tmp = sel.select('a/@href').extract()
            if tmp:
                url = urljoin(response.url, tmp[0])
                if '/product/' in url:
                    yield Request(url, meta={'brand':brand}, callback=self.parse_product)
                elif '/range/' in url:
                    yield Request(url, meta={'brand':brand}, callback=self.parse_range)
                else:
                    log.msg('!!! Unknown list page type at '+response.url)

        #To crawl next page.
        return ###
        tmp = None
        if tmp:
            #url = urljoin(response.url, tmp[0])
            yield Request(tmp[0], callback=self.parse_products_list)

    def parse_range(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)
        for link in hxs.select('//article//h2/a/@href').extract(): ###
            url = urljoin(response.url, link)
            yield Request(url, meta={'brand':response.meta['brand']}, callback=self.parse_product)

    def parse_product(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)

        tmp = hxs.select('//aside//input[@name="entry_id"]/@value').extract()
        if tmp:
            loader.add_value('identifier', tmp[0])
            loader.add_value('sku', tmp[0])
        else:
            log.msg('### No product ID at '+response.url, level=log.INFO)
            return
        #tmp = hxs.select('//input[@name="productId"]/@value').extract()
        #if tmp:
        #    loader.add_value('sku', tmp[0])
        name = ''
        tmp = hxs.select('//header[@id="page-header"]//h1/text()').extract()
        if tmp:
            name = tmp[0].strip()
            loader.add_value('name', name)
        else:
            log.msg('### No name at '+response.url, level=log.INFO)
        #price
        price = 0
        stock = 0
        tmp = hxs.select('//aside//span[@class="store_product_price"]/text()').extract()
        if tmp:
            price = extract_price(tmp[0].strip())
            loader.add_value('price', price)
            stock = 1
        #stock
        #stock = 0
        #tmp = hxs.select('//td[strong="In Stock: "]/text()').extract()
        #if tmp and 'yes' in ''.join(tmp).lower():
        #    stock = 1
        loader.add_value('stock', stock)
        #image_url
        tmp = hxs.select('//aside//div[@class="gallery"]/img/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            loader.add_value('image_url', url)
        #brand
        #tmp = hxs.select('//div[@class="product-name"]/h2/a/text()').extract()
        #if tmp:
        #    loader.add_value('brand', tmp[0])
        loader.add_value('brand', response.meta['brand'])
        #category
        tmp = hxs.select('//ol[contains(@class,"breadcrumbs")]/li/a/text()').extract()
        if len(tmp)>1:
            for s in tmp[1:]:
                loader.add_value('category', s)
        #shipping_cost
        #if price<20:
        #    loader.add_value('shipping_cost', 2.49)
        #elif price<50:
        #    loader.add_value('shipping_cost', 5.95)
        loader.add_value('shipping_cost', 39.00)

        product = loader.load_item()

        options = hxs.select('//aside//select[not(@name="item_qty")]')
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
        all_options = []
        for sel1 in options:
            opt = []
            for sel2 in sel1.select('option'):
                v=t=''
                tmp = sel2.select('@value').extract()
                if tmp:
                    v = tmp[0]
                tmp = sel2.select('text()').extract()
                if tmp:
                    t = tmp[0].strip()
                opt.append((v,t))
            all_options.append(opt)
        for opt in itertools.product(*all_options):
            #print opt
            item = copy.deepcopy(product)

            item['identifier'] += '-' + '-'.join([a[0] for a in opt])
            nm = '-'.join([a[1] for a in opt])
            p = float(price)
            for s in re.findall(r'\+.([\d,.]+)', nm):
                p += float(s)
                #print 'p', s
            item['price'] = extract_price(str(p))
            nm = re.sub(r'\(\+.[\d,.]+\)', '', nm).replace('\n','')
            nm = re.sub(r' +',' ',nm).replace(' -','-')
            item['name'] = name + ' - ' + nm

            if not item.get('identifier', None):
                log.msg('### No product ID at '+response.url, level=log.INFO)
            else:
                if not item['identifier'] in self.id_seen:
                    self.id_seen.append(item['identifier'])
                    yield item
                else:
                    log.msg('### Duplicate product ID at '+response.url, level=log.INFO)
            #break ###


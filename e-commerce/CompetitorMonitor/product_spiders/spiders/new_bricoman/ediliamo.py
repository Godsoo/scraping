import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
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

HERE = os.path.abspath(os.path.dirname(__file__))

class EdiliamoSpider(BaseSpider):
    name = 'ediliamo.com'
    allowed_domains = ['ediliamo.com']
    start_urls = ['http://www.ediliamo.com']

    def parse(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)
        for link in hxs.select('//div[@id="departments-box"]/div/ul/li/a/@href').extract(): ###
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        links = hxs.select('//div[@class="child-department-name"]/a/@href').extract()
        if links:
            #This is a sub-categories page
            for link in links: ###
                url = urljoin(response.url, link)
                yield Request(url, callback=self.parse_products_list)
            return
        #This is a product list page.
        for link in hxs.select('//div[@class="product-image"]/a/@href').extract(): ###
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_product)

        #To crawl next page.
        tmp = hxs.select('//div[@class="paging"]/a[text()="Successivi"]/@href').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            yield Request(url, callback=self.parse_products_list)

    def parse_product(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        #SKU
        tmp = hxs.select('//form[@action="/cart.html"]//input[@name="Id"]/@value').extract()
        if tmp:
            loader.add_value('identifier', tmp[0])
        tmp = hxs.select('//form[@action="/cart.html"]//input[@name="PSku"]/@value').extract()
        if tmp:
            loader.add_value('sku', tmp[0])
            #loader.add_value('identifier', tmp[0])
        #Name
        tmp = hxs.select('//div[@class="product"]//h1/text()').extract()
        if tmp:
            loader.add_value('name', tmp[0])
        #Price
        tmp = hxs.select('//dd[@class="product-price"]/span/text()').extract()
        if tmp:
            #tmp[0] = tmp[0].replace(u'\xa3','')
            tmp[0] = tmp[0].replace('.','').replace(',','.')
            price = extract_price(tmp[0])
            loader.add_value('price', price)
            loader.add_value('stock', 1)
        else:
            loader.add_value('stock', 0)
        #image_url
        tmp = hxs.select('//div[@id="design-product-image"]/a/img/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            loader.add_value('image_url', url)
        #Brand
        tmp = hxs.select('//div[@id="product-producer"]/a/text()').extract()
        if tmp:
            loader.add_value('brand', tmp[0])
        #Category
        tmp = hxs.select('//div[@class="breadcrumbs"]/ul/li/a/text()').extract()
        if tmp:
            loader.add_value('category', tmp[0])
        #Shipping
        #loader.add_value('shipping_cost', '6.00')
        #Stock
        #loader.add_value('stock', stock[0].strip())

        #To find options.
        sels = hxs.select('//div[@class="product-items"]/table/tbody/tr')
        if not sels:
            yield loader.load_item()
        else:
            for sel in sels: ###
                item = loader.load_item()
                tmp = sel.select('td[2]/text()').extract()
                if tmp:
                    item['sku'] = tmp[0]
                    item['identifier'] = item['identifier'] + '-' + tmp[0]
                tmp = sel.select('td[3]/text()').extract()
                if tmp:
                    item['name'] = item['name'] + ' - ' + tmp[0]
                tmp = sel.select('td[4]/span/span/text()').extract()
                if tmp:
                    tmp[0] = tmp[0].replace('.','').replace(',','.')
                    item['price'] = extract_price(tmp[0])
                yield item


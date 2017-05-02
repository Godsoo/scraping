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

class TechnogadgetsSpider(BaseSpider):
    name = 'technogadgets'
    #download_delay = 3
    allowed_domains = ['technogadgets.com.sg']
    start_urls = ['http://www.technogadgets.com.sg/']
    #cookie_num = 0
    #brands = []
    id_seen = []

    def parse(self, response):
        #inspect_response(response, self)
        #yield Request('http://www.ecookshop.co.uk/ecookshop/product.asp?pid=962009161', callback=self.parse_product)
        #return
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//ul[@id="mainmenu-nav"]/li/a/@href').extract()[1:]: ###
            #url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_products_list)

    def parse_products_list(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//table[@class="tblList"]//tr//a[contains(@href,"/prod_")][1]/@href').extract(): ###
            #url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_product)

        #To crawl next page.
        #return ###
        tmp = hxs.select('//div[@class="pagination"]//a[text()=">"]/@href').extract()
        if tmp:
            #url = urljoin(response.url, tmp[0])
            yield Request(tmp[0], callback=self.parse_products_list)

        #Crawl subcategories.
        #return ###
        if not 'page=' in response.url:
            #First page.
            for url in hxs.select('//div[@id="subCats"]/div/a[1]/@href').extract(): ###
                yield Request(url, callback=self.parse_products_list)

    def parse_product(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        tmp = hxs.select('//input[@name="add"]/@value').extract()
        if tmp:
            loader.add_value('identifier', tmp[0].strip())
        else:
            log.msg('### No product ID at '+response.url, level=log.INFO)
            return
        #tmp = hxs.select('//input[@name="add"]/@value').extract()
        r = re.findall(r'<strong>Product Code:</strong> {0,3}(\w+)', response.body)
        if r:
            loader.add_value('sku', r[0])
        name = ''
        tmp = hxs.select('//p[@class="txtContentTitle"]/strong/text()').extract()
        if tmp:
            name = tmp[0].strip()
            loader.add_value('name', name)
        else:
            log.msg('### No name at '+response.url, level=log.INFO)
        #price
        price = 0
        tmp = hxs.select('//p[strong="Price:"]/text()').extract()
        if tmp:
            tmp1 = [s.strip() for s in tmp if '$' in s]
            if tmp1:
                price = extract_price(tmp1[0].strip())
        tmp = hxs.select('//p[strong="Price:"]/span[@class="txtSale"]/text()').extract()
        if tmp:
            price = extract_price(tmp[0].strip())
        loader.add_value('price', price)
        #stock
        stock = 0
        if price:
            stock = 1
        loader.add_value('stock', stock)
        #image_url
        tmp = hxs.select('//p[@class="txtContentTitle"]/following-sibling::div/img/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0].replace(' ','%20'))
            loader.add_value('image_url', url)
        #brand
        if name:
            loader.add_value('brand', name.split()[0])
        #category
        for s in hxs.select('//a[preceding-sibling::strong="Location:" and following-sibling::form]/text()').extract():
            loader.add_value('category', s)
        #shipping_cost
        loader.add_value('shipping_cost', 15)

        product = loader.load_item()

        if not product['identifier'] in self.id_seen:
            self.id_seen.append(product['identifier'])
            yield product
        else:
            log.msg('### Duplicate product ID at '+response.url, level=log.INFO)


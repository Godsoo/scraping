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

from urlparse import urljoin, urlparse, urlunparse

import itertools
import json
import copy
import lxml

HERE = os.path.abspath(os.path.dirname(__file__))

class WowwigsSpider(BaseSpider):
    name = 'wowwigs'
    #download_delay = 1
    allowed_domains = ['wowwigs.com']
    start_urls = ['http://www.wowwigs.com']
    #cookie_num = 0
    #brands = []
    id_seen = []

    def parse(self, response):
        #inspect_response(response, self)
        #yield Request('http://www.wowwigs.com/autumn-henry-margu-wig1.html', callback=self.parse_product)
        #return
        hxs = HtmlXPathSelector(response)
        #for link in hxs.select('//center[b/a="Shop by Brand"]/following-sibling::ul/li/a/@href').extract(): ###
        for url in hxs.select('//div[@id="display_menu_1"]//a/@href').extract(): ###
            #url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_products_list)

    def parse_products_list(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        #Crawl subcategories.
        links = hxs.select('//div[@class="sectcontents"]//div[@class="name"]/a/@href').extract()
        if links:
            for link in links: ###
                url = urljoin(response.url, link)
                yield Request(url, callback=self.parse_products_list)
            return

        #inspect_response(response, self)
        #return
        #Crawl product list
        links = hxs.select('//table[contains(@class, "productDisplay")]//a/@href').extract()
        for link in links: ###
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_product)

        #To crawl next page.
        pages = hxs.select('//select[@class="results_per_page_select"]/../nobr//b/text()').re('\d+')
        if pages:
            pages = int(pages[0])
            parts = list(urlparse(response.url))
            for page in xrange(2, pages+1):
                parts[4] = 'show=20&page=%d' %page
                yield Request(urlunparse(parts), callback=self.parse_products_list)

    def parse_product(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        tmp = hxs.select('//span[@class="product_code"]/text()').extract()
        if tmp:
            loader.add_value('identifier', tmp[0].strip())
            loader.add_value('sku', tmp[0])
        else:
            log.msg('### No product ID at '+response.url, level=log.INFO)
            return
        #tmp = hxs.select('//input[@name="productId"]/@value').extract()
        #if tmp:
        #    loader.add_value('sku', tmp[0])
        name = ''
        tmp = hxs.select('//span[@itemprop="name"]/text()').extract()
        if tmp:
            name = tmp[0].strip()
            loader.add_value('name', name)
        else:
            log.msg('### No name at '+response.url, level=log.INFO)
        #price
        price = 0
        stock = 0
        tmp = hxs.select('//span[@itemprop="price"]/text()').extract()
        if not tmp:
            tmp = hxs.select('//table[@id="product-info-table"]/tr[@class="price"]/td/span[1]/text()').extract()
        if tmp:
            price = extract_price(tmp[0].strip().replace(',',''))
            loader.add_value('price', price)
            stock = 1
        #stock
        #stock = 0
        #tmp = hxs.select('//td[strong="In Stock: "]/text()').extract()
        #if tmp and 'yes' in ''.join(tmp).lower():
        #    stock = 1
        loader.add_value('stock', stock)
        #image_url
        tmp = hxs.select('//img[@id="product_photo"]//@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0].strip())
            loader.add_value('image_url', url)
        #brand
        tmp = hxs.select('//span[@itemprop="description"]//b[1]/text()').extract()
        if tmp:
            loader.add_value('brand', tmp[0].replace('Collection', '').strip())
        #category
        tmp = hxs.select('//div[@class="breadbox"]/div[1]/a/text()').extract()
        if len(tmp)>1:
            for s in tmp[1:]:
                loader.add_value('category', s)
        #shipping_cost
        if Decimal(price) < 49.95:
            loader.add_value('shipping_cost', '8.95')

        product = loader.load_item()

        options = hxs.select('//table[@id="options_table"]//select/option[@value!="0"]')
        #No options currently.
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
        for sel in options: ###
            item = copy.deepcopy(product)
            tmp = sel.select('./text()').extract()
            if tmp:
                item['identifier'] += '-' + tmp[0].replace(' ','_')
                item['name'] = name + ' - ' + tmp[0]

            if not item.get('identifier', None):
                log.msg('### No product ID at '+response.url, level=log.INFO)
            else:
                if not item['identifier'] in self.id_seen:
                    self.id_seen.append(item['identifier'])
                    yield item
                else:
                    log.msg('### Duplicate product ID at '+response.url, level=log.INFO)


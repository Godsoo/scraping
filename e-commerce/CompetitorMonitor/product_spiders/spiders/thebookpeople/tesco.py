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

import re
import os

from scrapy.item import Item, Field

HERE = os.path.abspath(os.path.dirname(__file__))

class YMeta(Item):
    #promotions = Field()
    Pre_Order = Field()
    Author = Field()
    Format = Field()
    Publisher = Field()
    Published = Field()

class TescoSpider(BaseSpider):
    name = 'tesco'
    #download_delay = 3
    #allowed_domains = ['ecookshop.co.uk']
    start_urls = ['http://www.tesco.com/direct/books/?icid=ents_navstamp_slot2']
    cookie_num = 0
    #brands = []
    id_seen = []

    def parse(self, response):
        #inspect_response(response, self)
        #yield Request('http://www.tesco.com/direct/the-girl-in-the-spiders-web/S73-F8C5.prd?pageLevel=&skuId=S73-F8C5', callback=self.parse_product)
        #return
        hxs = HtmlXPathSelector(response)
        for link in hxs.select('//h2[text()="All Books categories"]/following-sibling::ul/li/a/@href').extract(): ###
            url = urljoin(response.url, link)
            self.cookie_num += 1
            yield Request(url, meta={'cookiejar':self.cookie_num},callback=self.parse_products_list)

    def parse_products_list(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)
        links = hxs.select('//ul[@class="products"][1]/li//h3//a[1]/@href').extract()
        for link in links: ###
            url = urljoin(response.url, link)
            yield Request(url, meta={'cookiejar': response.meta['cookiejar']}, callback=self.parse_product)

        #To crawl next page.
        #http://www.tesco.com/direct/entertainment-books/biography-autobiography/cat3376542.cat?catId=4294869017
        #http://www.tesco.com/direct/blocks/catalog/productlisting/infiniteBrowse.jsp?&view=grid&catId=4294869017&sortBy=1&searchquery=&offset=20&lazyload=true
        #http://www.tesco.com/direct/blocks/catalog/productlisting/infiniteBrowse.jsp?&view=grid&catId=4294869017&sortBy=1&searchquery=&offset=40&lazyload=true
        ###
        #http://www.tesco.com/direct/entertainment-books/cookery/cat3376636.cat?catId=4294867307
        #http://www.tesco.com/direct/blocks/catalog/productlisting/infiniteBrowse.jsp?&view=grid&catId=4294867307&sortBy=1&searchquery=&offset=20&lazyload=true
        #http://www.tesco.com/direct/blocks/catalog/productlisting/infiniteBrowse.jsp?&view=grid&catId=4294867307&sortBy=1&searchquery=&offset=40&lazyload=true
        #return ###
        #tmp = None
        if len(links)==20:
            r = re.findall(r'catId=(\d+)', response.url)
            if r:
                url = 'http://www.tesco.com/direct/blocks/catalog/productlisting/infiniteBrowse.jsp?&view=grid&catId=%s&sortBy=1&searchquery=&offset=20&lazyload=true' % r[0]
                #url = urljoin(response.url, tmp[0])
                yield Request(url, method='POST', headers={'Accept':'application/json, text/javascript, */*; q=0.01', 'AjaxRequest':'getProducts', 'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8'}, body=url.split('.jsp?',1)[1], meta={'cookiejar': response.meta['cookiejar']}, callback=self.parse_products_more)

    def parse_products_more(self, response):
        #inspect_response(response, self)
        #return
        #print 'response:', response.body[:500]
        j = json.loads(response.body)
        hxs = HtmlXPathSelector(text=j['products'])
        links = hxs.select('//li//h3//a[1]/@href').extract()
        for link in links: ###
            url = urljoin(response.url, link)
            yield Request(url, meta={'cookiejar': response.meta['cookiejar']}, callback=self.parse_product)

        #Crawl next page.
        if len(links)==20:
            r = re.findall(r'offset=(\d+)', response.url)
            if r:
                off = int(r[0]) + 20
                url = re.sub(r'offset=\d+', 'offset='+str(off), response.url)
                #url = urljoin(response.url, tmp[0])
                yield Request(url, method='POST', headers={'Accept':'application/json, text/javascript, */*; q=0.01', 'AjaxRequest':'getProducts', 'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8'}, body=url.split('.jsp?',1)[1], meta={'cookiejar': response.meta['cookiejar']}, callback=self.parse_products_more)

    def parse_product(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        tmp = response.xpath('//div[@class="book"]/ul/li[strong="ISBN:"]/text()').extract()
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
        tmp = hxs.select('//h1[@itemprop="name"]/text()').extract()
        if tmp:
            name = tmp[0].strip()
            loader.add_value('name', name)
        else:
            log.msg('### No name at '+response.url, level=log.INFO)
        #price
        price = 0
        tmp = hxs.select('//div[@class="price-info"]/p[@itemprop="price"]/text()').extract()
        if tmp:
            price = extract_price(tmp[0].strip().replace(',',''))
            loader.add_value('price', price)
        #stock
        stock = 0
        tmp = hxs.select('//div[@class="buy"]//input[@value="Add to basket"]')
        if tmp:
            stock = 1
        loader.add_value('stock', stock)
        #image_url
        tmp = hxs.select('//div[@class="static-product-image"]/img/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            loader.add_value('image_url', url)
        #brand
        tmp = hxs.select('//div[@class="details-container"]/p[@class="author"]/text()').extract()
        if tmp:
            loader.add_value('brand', tmp[0].replace('By:','').strip())
        #category
        tmp = hxs.select('//div[@id="breadcrumb"]/ul/li/a/span/text()').extract()
        if len(tmp)>4:
            for s in tmp[3:-1]:
                loader.add_value('category', s.strip())
        #shipping_cost
        #if price<20:
        #    loader.add_value('shipping_cost', 2.49)
        #elif price<50:
        #    loader.add_value('shipping_cost', 5.95)

        product = loader.load_item()

        #metadata
        metadata = YMeta()
        #Pre_Order
        tmp = hxs.select('//div[@class="buy"]//input[@value="Pre-order"]')
        if tmp:
            metadata['Pre_Order'] = 'Yes'
        #Author
        tmp = hxs.select('//div[@class="book"]/ul/li[strong="Author: "]/text()').extract()
        if tmp:
            metadata['Author'] = ''.join(tmp).strip()
        #Format
        tmp = hxs.select('//div[@class="book"]/ul/li[strong="Format: "]/text()').extract()
        if tmp:
            metadata['Format'] = ''.join(tmp).strip()
        #Publisher
        tmp = hxs.select('//div[@class="book"]/ul/li[strong="Publisher: "]/text()').extract()
        if tmp:
            metadata['Publisher'] = ''.join(tmp).strip()
            product['brand'] = ''.join(tmp).strip()
        #Published
        tmp = hxs.select('//div[@class="book"]/ul/li[strong="Published: "]/text()').extract()
        if tmp:
            metadata['Published'] = ''.join(tmp).strip()

        if metadata:
            product['metadata'] = metadata

        options = None
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
        #No options currently.
        #for sel in options[0:1]: ###
        #    item = copy.deepcopy(product)


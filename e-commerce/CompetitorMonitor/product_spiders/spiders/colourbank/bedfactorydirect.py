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

class BedfactorydirectSpider(BaseSpider):
    name = 'bedfactorydirect'
    #download_delay = 1
    allowed_domains = ['bedfactorydirect.co.uk']
    start_urls = ['http://www.bedfactorydirect.co.uk/']
    #cookie_num = 0
    #brands = []
    id_seen = []

    def parse(self, response):
        #inspect_response(response, self)
        #yield Request('http://www.bedfactorydirect.co.uk/cassandra-adjustable-bed', meta={'categories':['test']}, callback=self.parse_product)
        #return
        hxs = HtmlXPathSelector(response)

        for sel in hxs.select('//ul[contains(@class,"nav")]/li')[1:5]: ###
            category = None
            tmp = sel.select('a/span/text()').extract()
            if tmp:
                category = tmp[0]
            for sel2 in sel.select('.//li[@class="   "]/a'): ###
                if category:
                    subcategory = [category]
                else:
                    subcategory = []
                tmp = sel2.select('span/text()').extract()
                if tmp:
                    subcategory += [tmp[0],]
                tmp = sel2.select('@href').extract()
                if tmp:
                    yield Request(tmp[0], meta={'categories':subcategory}, callback=self.parse_products_list)
                #print category, subcategory, sel2.select('@href').extract()

    def parse_products_list(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        #Crawl product list
        links = hxs.select('//div[@id="products-grid"]//h3/a/@href').extract()
        for link in links: ###
            #url = urljoin(response.url, link)
            url = link
            yield Request(url, meta={'categories':response.meta['categories']}, callback=self.parse_product)

        #To crawl next page.
        #return ###
        tmp = hxs.select('//div[@class="pages"]//a[@class="next"]/@href').extract()
        if tmp:
            #url = urljoin(response.url, tmp[0])
            yield Request(tmp[0], meta={'categories':response.meta['categories']}, callback=self.parse_products_list)

    def parse_product(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)

        tmp = hxs.select('//input[@name="product"]/@value').extract()
        j1 = None
        if 'new Product.OptionsPrice(' in response.body:
            d = response.body.split('new Product.OptionsPrice(',1)[1].split(');',1)[0]
            j1 = json.loads(d)
        if j1 and j1.get('productId',None):
            loader.add_value('identifier', j1['productId'])
            loader.add_value('sku', j1['productId'])
        elif tmp:
            loader.add_value('identifier', tmp[0])
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
        stock = 0
        tmp = hxs.select('//div[@itemprop="offerDetails"]//span[@class="price"]/text()').extract()
        if j1:
            price = extract_price(str(j1.get('productPrice','')))
            loader.add_value('price', price)
            stock = 1
        elif tmp:
            price = extract_price(tmp[-1])
            loader.add_value('price', price)
            stock = 1
        #stock
        #stock = 0
        #tmp = hxs.select('//td[strong="In Stock: "]/text()').extract()
        #if tmp and 'yes' in ''.join(tmp).lower():
        #    stock = 1
        loader.add_value('stock', stock)
        #image_url
        tmp = hxs.select('//img[@id="image"]/@src').extract()
        if tmp:
            #url = urljoin(response.url, tmp[0].strip())
            loader.add_value('image_url', tmp[0])
        #brand
        #tmp = hxs.select('//div[@class="product-name"]/h2/a/text()').extract()
        #if tmp:
        #    loader.add_value('brand', tmp[0])
        #category
        #tmp = hxs.select('//div[@class="breadcrumbs"]/ul/li/a/text()').extract()
        #if len(tmp)>1:
        for s in response.meta['categories']:
            loader.add_value('category', s)
        #shipping_cost
        #if price<20:
        #    loader.add_value('shipping_cost', 2.49)
        #elif price<50:
        #    loader.add_value('shipping_cost', 5.95)

        product = loader.load_item()

        #options = hxs.select('//table[@id="product-info-table"]//select/option')
        #options = None
        #if 'new Product.Config(' in response.body:
        #    d = response.body.split('new Product.Config(',1)[1].split(');',1)[0]
        #    j2 = json.loads(d)
        #    try:
        #        options = j2['attributes']['92']['options']
        #    except:
        #        pass
        options = hxs.select('//div[@itemprop="description"]//select')
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
            for sel2 in sel1.select('option[@price]'):
                v=p=t=''
                tmp = sel2.select('@value').extract()
                if tmp:
                    v = tmp[0]
                tmp = sel2.select('@price').extract()
                if tmp:
                    p = tmp[0]
                tmp = sel2.select('text()').extract()
                if tmp:
                    t = tmp[0].strip()
                opt.append((v,p,t))
            all_options.append(opt)
        for opt in itertools.product(*all_options):
            #print opt
            #print 'price', price, type(price)
            item = copy.deepcopy(product)

            item['identifier'] += '-' + '-'.join([a[0] for a in opt])
            item['name'] = name + ' - ' + '-'.join([a[2] for a in opt])
            item['name'] = re.sub(r' \+\xa3[\d.,]+','',item['name'])
            p = price
            for s in [a[1] for a in opt]:
                p += int(s)
                #print 'p', s
            item['price'] = p

            if not item.get('identifier', None):
                log.msg('### No product ID at '+response.url, level=log.INFO)
            else:
                if not item['identifier'] in self.id_seen:
                    self.id_seen.append(item['identifier'])
                    yield item
                else:
                    log.msg('### Duplicate product ID at '+response.url, level=log.INFO)
            #break ###


import re
import os
from decimal import Decimal

from collections import defaultdict
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
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from urlparse import urljoin

import itertools
import json
import copy

HERE = os.path.abspath(os.path.dirname(__file__))

class JohnlewisSpider(BaseSpider):

    name               = 'made-johnlewis'
    allowed_domains    = ['johnlewis.com']
    start_urls         = ['http://www.johnlewis.com/home-garden/c500006']
    id_seen            = []
    rotate_agent       = True
    name_rules = []

    def start_requests(self):
        self.idle_called = False
        dispatcher.connect(self.spider_idle, signals.spider_idle)
        country_url = "http://www.johnlewis.com/store/international/ajax/changeCountryAjaxRequest.jsp"
        formdata = {'country': 'GB',
                    'sourceUrl': 'http://www.johnlewis.com/home-garden/c500006',
                    'switchToggle': 'Change Country Overlay'}
        yield FormRequest(country_url, formdata=formdata, callback=self.initial_parse)

    def spider_idle(self, spider):
        self.log('spider idle called')
        if spider.name == self.name and not self.idle_called:
            self.idle_called = True
            req = Request('http://www.johnlewis.com/home-garden/c500006', dont_filter=True)
            self.crawler.engine.crawl(req, self)

    def _select_category(self, product_name, response, site_cat):
        if type(product_name) == list:
            name = ''.join(product_name)
        else:
            name = product_name

        for cat, text in self.name_rules:
            name = product_name.lower()
            found = True
            for word in text.split(' '):
                if word.startswith('!') and word[1:].lower() in name:
                    found = False
                if not word.startswith('!') and word.lower() not in name:
                    found = False

            if found:
                self.log('Category matched')
                return cat
        if not response.meta.get('rules'):
            return site_cat
        for rule in response.meta['rules']:
            name = name.lower()
            found = True
            for word in rule['text'].split(' '):
                if word.startswith('!') and word[1:].lower() in name:
                    found = False
                if not word.startswith('!') and word.lower() not in name:
                    found = False

            if found:
                self.log('Category matched')
                return rule['category']

        return site_cat

    def initial_parse(self, response):
        category_rules = defaultdict(list)
        with open(os.path.join(HERE, 'lewis_cats.csv')) as f:
            reader = csv.reader(f)
            for row in reader:
                url, category, text = row
                category = category.split('>')
                category = [c.decode('utf8').strip() for c in category]
                if not url:
                    self.name_rules.append([category, text])
                else:
                    category_rules[url.decode('utf8')].append({'category': category,
                                                               'text': text.decode('utf8')})

        for url in category_rules:
            yield Request(url, callback=self.parse_product_list, meta={'rules': category_rules[url]})


    def parse_product_list(self, response):
        #== Crawl subcategories ==#
        hxs   = HtmlXPathSelector(response)

        #== Crawl product list ==#
        links = hxs.select('//div[@class="products"]/div/article/a/@href').extract()
        for link in links:
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_product, meta=response.meta)

        #== Crawl next page ==#
        tmp = hxs.select('//div[@class="pagination"]//a[@rel="next"]/@href').extract()
        if not tmp:
            tmp = hxs.select('//div[@class="pagination"]//li[@class="next"]/a/@href').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            yield Request(url, callback=self.parse_product_list, meta=response.meta)

    def parse(self, response):
        #== Crawl subcategories ==#
        hxs   = HtmlXPathSelector(response)
        links = hxs.select('//div[@class="col-3 first lt-nav"]//li/a/@href').extract()
        if links:
            for link in links:
                url = urljoin(response.url, link)
                if 'home-garden' in url:
                    yield Request(url, callback=self.parse)
            return

        #== Crawl product list ==#
        links = hxs.select('//div[@class="products"]/div/article/a/@href').extract()
        for link in links:
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_product)

        #== Product options ==#
        #links = hxs.select('//div[@class="products"]/div//ul[@class="selection-grid"]//a/@href').extract()
        #for link in links:
        #    url = urljoin(response.url, link)
        #    yield Request(url, callback=self.parse_product)

        #== Crawl next page ==#
        tmp = hxs.select('//div[@class="pagination"]//a[@rel="next"]/@href').extract()
        if not tmp:
            tmp = hxs.select('//div[@class="pagination"]//li[@class="next"]/a/@href').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            yield Request(url, callback=self.parse)

    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)

        sub_items = hxs.select('//div[@class="item-details"]//h3/a/@href').extract()
        if sub_items:
            for sub_item in sub_items:
                url = urljoin(response.url, sub_item)
                yield Request(url, callback=self.parse_product, meta=response.meta)
            return

        option_links = hxs.select('//form[@id="save-product-to-cart"]//div/ul[contains(@class, "selection-grid")]/li/a/@href').extract()
        if not response.meta.get('option', False) and option_links:
            for link in option_links:
                url = urljoin(response.url, link)
                yield Request(url, meta={'option':True, 'rules': response.meta.get('rules')},
                              dont_filter=True, callback=self.parse_product)
            return

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)


        #== Extracting Identifier and SKU ==#
        tmp = hxs.select('//div[@id="prod-product-code"]/p/text()').extract()
        if not tmp:
            tmp = hxs.select('//div[@id="bundle-product-code"]/p/text()').extract()
        if tmp:
            loader.add_value('identifier', tmp[0])
            loader.add_value('sku', tmp[0])


        #== Extracting Product Name ==#
        name = ''
        try:
            name = hxs.select('//h1[@id="prod-title"]/span/text()').extract()[0].strip()
        except:
            try:
                name = hxs.select("//div[@class='mod mod-product-info']/h2/text()").extract()[0].strip()
            except:
                name = hxs.select('//h1[@id="prod-title"]/text()').extract()
                if name:
                    name = name[0].strip()
                else:
                    name = hxs.select('//h1/span[@itemprop="name"]/text()').extract()
                    if name:
                        name = name[0].strip()
                    else:
                        log.msg('### No name at '+ response.url, level=log.INFO)

        tmp = hxs.select('//div[@class="detail-pair"]/p/text()').extract()
        if tmp:
            name += ', ' + tmp[0]
        loader.add_value('name', name)


        #== Extracting Price, Stock & Shipping cost ==#
        price = 0
        stock = 0
        tmp   = hxs.select('//div[@class="basket-fields"]/meta[@itemprop="price"]/@content').extract()
        if not tmp:
            tmp = hxs.select('//section[div[@id="prod-product-code"]]//div[@id="prod-price"]/p//strong//text()').extract()
            if not tmp:
                tmp = hxs.select('//div[@id="prod-price"]//span[@itemprop="price"]/text()').extract()
                if not tmp:
                    tmp = hxs.select('//strong[@class="price"]/text()').extract()
        if tmp:
            price = extract_price(''.join(tmp).strip().replace(',',''))
            stock = 1
            if Decimal(price) < 50.0:
                loader.add_value('shipping_cost', '3.00')
        loader.add_value('price', price)
        loader.add_value('stock', stock)

        #== Extracting Image URL ==#
        tmp = hxs.select('//li[contains(@class,"image")]//img/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            loader.add_value('image_url', url)
        

        #== Extracting Brand ==#
        tmp = hxs.select('//div[@itemprop="brand"]/span/text()').extract()
        if tmp:
            loader.add_value('brand', tmp[0].strip())
        

        #== Extracting Category ==#
        tmp = hxs.select('//div[@id="breadcrumbs"]/ol/li/a/text()')[1:].extract()
        # tmp = self._select_category(name, response, tmp)
        if len(tmp)>1:
            loader.add_value('category', ' > '.join(tmp))

        price = loader.get_output_value('price')
        if price:
            price = Decimal(price)
            if price < 50.0:
                loader.add_value('shipping_cost', '3.00')


        product = loader.load_item()


        #== Extracting Options ==#
        options = hxs.select('//div[@id="prod-multi-product-types"]//div[@itemprop="offers"]')
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

        #== Process options ==#
        for sel in options:
            item = copy.deepcopy(product)
            tmp  = sel.select('.//div[contains(@class,"mod-product-code")]/p/text()').extract()
            if tmp:
                item['identifier'] = tmp[0]
                item['sku'] = tmp[0]
            tmp = sel.select('.//h3/text()').extract()
            if tmp:
                item['name'] = name + ' - ' + tmp[0]

            price = 0
            tmp = sel.select('.//p[@class="price"]/strong/text()').re('[0-9,.]+')
            if not tmp:
                tmp = sel.select('.//strong[@class="price"]/text()').re('[0-9,.]+')
            if tmp:
                price = extract_price(tmp[0].strip().replace(',',''))
                if Decimal(price) < 50.0:
                    item['shipping_cost'] = '3.00'
                else:
                    item['shipping_cost'] = '0'
            item['price'] = price

            tmp = sel.select('.//link[@itemprop="availability"]/@content').extract()
            if tmp and 'in' in tmp[0].lower():
                item['stock'] = 1
            else:
                item['stock'] = 0

            if not item.get('identifier', None):
                log.msg('### No product ID at '+response.url, level=log.INFO)
            else:
                if not item['identifier'] in self.id_seen:
                    self.id_seen.append(item['identifier'])
                    yield item
                else:
                    log.msg('### Duplicate product ID at '+response.url, level=log.INFO)

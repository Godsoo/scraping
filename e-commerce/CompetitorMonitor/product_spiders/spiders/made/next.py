import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
import hashlib
from collections import defaultdict
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

class NextSpider(BaseSpider):
    name = 'next.co.uk'
    allowed_domains = ['next.co.uk']
    start_urls = ['http://www.next.co.uk/homeware']
    cookie_num = 0
    id_seen = []
    name_rules = []

    def start_requests(self):
        dispatcher.connect(self.spider_idle, signals.spider_idle)
        category_rules = defaultdict(list)
        with open(os.path.join(HERE, 'next_cats.csv')) as f:
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
            yield Request(url, callback=self.parse_products_list2, meta={'rules': category_rules[url],
                                                                         'limit': 1})

    def spider_idle(self, spider):
        self.log('spider idle called')
        if spider.name == self.name:
            req = Request('http://www.next.co.uk/homeware')
            self.crawler.engine.crawl(req, self)

    def _select_category(self, product_name, response, site_cat):
        self.log('matching: {}'.format(response.meta.get('rules')))
        for cat, text in self.name_rules:
            name = product_name.lower()
            found = True
            for word in text.split(' '):
                if word.lower() not in name:
                    found = False

            if found:
                self.log('Category matched')
                return cat

        if not response.meta.get('rules'):
            return site_cat
        for rule in response.meta['rules']:
            name = product_name.lower()
            found = True
            for word in rule['text'].split(' '):
                if word.lower() not in name:
                    found = False

            if found:
                self.log('Category matched')
                return rule['category']

        return site_cat


    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        links = hxs.select('//div[@class="Grid"]/div/div/a/@href').extract()
        for link in links:  
            url = urljoin(response.url, link)
            if 'mothersday' in url:
                continue
            yield Request(url, callback=self.parse_products_list, dont_filter=True)

        yield Request('http://www.next.co.uk/CustomData/sofastyles',
                      callback=self.parse_sofas_list, dont_filter=True)

    def parse_sofas_list(self, response):
        j = json.loads(response.body)

        for c in j['Categories']:
            for s in c['Styles']:  
                for d in s['Sizes']:  
                    url = 'http://www.next.co.uk/homeware/sofas-chairs/' + d['Url']
                    yield Request(url, callback=self.parse_sofa)


    def parse_sofa(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        options = hxs.select('//div[@class="tabCollection"]/div/div/div//article/a/@href').extract()
        for option in options:
            yield Request(urljoin_rfc(base_url, option), callback=self.parse_sofa)

        sku = hxs.select('//input[@id="hdnItemNumber"]/@value').extract()
        variant_id = hxs.select('//input[@id="hdnOptionCode"]/@value').extract()
        if sku and variant_id:
            image_url = hxs.select('//section[@class="media"]/ul[@class="images"]/li[1]/img/@src').extract()
            name = "".join(hxs.select('//section[@class="details"]/h1[@class="itemProperties"]//text()').extract()) 
            if not name:
                name = "".join(hxs.select('//section[@class="details"]/h2//text()').extract())

            price = hxs.select('//div[@class="selectedPrice"]/span[@class="price"]/text()').extract()
            identifier = "%s_%s" % (sku[0], variant_id[0])
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('identifier', identifier)
            loader.add_value('url', response.url)
            cat = self._select_category(name, response, '')
            if cat:
                for c in cat:
                    loader.add_value('category', c)
            elif 'bed' not in name.lower():
                loader.add_value('category', 'Home & Furniture')
                loader.add_value('category', 'Sofas & Armchairs')
            else:
                loader.add_value('category', 'Bedroom')
                loader.add_value('category', 'Sofa Bed')

            if image_url:
                loader.add_value('image_url', image_url[0])
            if price:
                loader.add_value('price', price[0])
                loader.add_value('stock', 1)
            else:
                loader.add_value('price', 0)
                loader.add_value('stock', 0)
            loader.add_value('shipping_cost', '3.99')
            yield loader.load_item()

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)

        links = hxs.select('//map/area/@href').extract()
        links += hxs.select('//div[@class="Grid"]//a/@href').extract()
        if not links:
            links = hxs.select('//div[@class="StorefrontContent "]/div//ul/li/a/@href').extract()
        if links:
            # Crawl subcategories.
            for link in links:  # ##
                url = urljoin(response.url, link)
                yield Request(url, callback=self.parse_products_list, meta=response.meta)

        # Crawl product list.
        for link in hxs.select('//div[@id="rhs"]//article//h2/a/@href').extract():  # ##
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_product, meta=response.meta)

        # To crawl next page.
        #return ###
        tmp = hxs.select('//link[@rel="next"]/@href').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            yield Request(url, callback=self.parse_products_list, meta=response.meta)

        for product in self.parse_product(response):
            yield product

    def parse_products_list2(self, response):
        hxs = HtmlXPathSelector(response)
        '''
        links = hxs.select('//map/area/@href').extract()
        links += hxs.select('//div[@class="Grid"]//a/@href').extract()
        if not links:
            links = hxs.select('//div[@class="StorefrontContent "]/div//ul/li/a/@href').extract()
        if links:
            # Crawl subcategories.
            for link in links:  # ##
                url = urljoin(response.url, link)
                yield Request(url, callback=self.parse_products_list, meta=response.meta)
        '''
        # Crawl product list.
        links = hxs.select('//div[@id="rhs"]//article//h2/a/@href').extract()
        links += hxs.select('//div[@id="rhs"]//article//img/@data-url').extract()
        for link in hxs.select('//div[@id="rhs"]//article//h2/a/@href').extract():  # ##
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_product, meta=response.meta)

        # To crawl next page.
        #return ###
        tmp = hxs.select('//link[@rel="next"]/@href').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            yield Request(url, callback=self.parse_products_list2, meta=response.meta)

    def parse_single(self, response, hxs):
        ident = hxs.select('.//input[@id="hdnItemNumber"]/@value')
        self.log('Parse single called %s' % ident)
        if not ident:
            return

        loader = ProductLoader(item=Product(), selector=hxs)
        cat = hxs.select('//div[@class="BreadcrumbsHolder"]//ul/li/a/text()').extract()
        if len(cat) > 1:
            cat = cat[1:]
        if len(cat) > 1:
            cat = cat[:-1]
        loader.add_value('shipping_cost', '3.99')
        loader.add_xpath('name', '//section[@class="details"]/h2/text()')
        loader.add_xpath('price', '//div[@class="selectedPrice"]/span[@class="price"]/text()')
        loader.add_value('url', response.url)
        sku = hxs.select('.//div[@class="ItemNumber"]/text()')
        if sku:
            loader.add_value('sku', sku[0].extract())
        loader.add_xpath('identifier', './/input[@id="hdnItemNumber"]/@value')
        image_url = response.xpath('.//ul[@class="images"]//img/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])

        product = loader.load_item()
        cat = self._select_category(product['name'], response, cat)
        if cat:
            product['category'] = ' > '.join(cat)

        return product

    # GET http://www.next.co.uk/item/687447x54?CTRL=select
    # GET http://www.next.co.uk/item/827420x55?CTRL=select
    # GET http://www.next.co.uk/item/804045x55?CTRL=select
    # POST http://www.next.co.uk/bag/add
    # id:892378X54
    # option:55
    # quantity:1
    def parse_product(self, response):
        # inspect_response(response, self)
        # return
        hxs = HtmlXPathSelector(response)
        single = self.parse_single(response, hxs)
        if single:
            yield single

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        cat = hxs.select('//div[@id="ProductDefaultBreadcrumb"]//ul/li/a/text()').extract()
        if len(cat) > 1:
            cat = cat[1:]
        if len(cat) > 1:
            cat = cat[:-1]

        loader.add_value('shipping_cost', '3.99')

        product = loader.load_item()

        rows = hxs.select('//section[@class="ProductDetail"]/article')
        if not rows:
            log.msg('### No product found at ' + response.url, level=log.INFO)
            return
        # process options
        limit = None
        if response.meta.get('limit'):
            limit = 1
        for sel in rows[:limit] if limit else rows:  # ##
            name = ''
            tmp = sel.select('.//div[@class="Title"]/*[self::h1 or self::h2]//text()').extract()
            if tmp:
                name = ''.join([x for x in tmp]).strip()

            cat = self._select_category(name, response, cat)
            if cat:
                product['category'] = ' > '.join(cat)

            price = 0
            tmp = sel.select('.//div[@class="Price"]/text()').extract()
            if tmp:
                price = extract_price(tmp[0].strip())

            sku = sel.select('.//div[@class="ItemNumber"]/text()')[0].extract()


            options = sel.select('.//div[@class="DropDown"][1]//option')
            if options:
                # process options
                for opt_sel in options:  # ##
                    tmp = opt_sel.select('@value').extract()
                    if not tmp:
                        continue
                    id1 = tmp[0]
                    if not '-' in id1:
                        id1 = '%s-%s' % (sel.select('.//div[@class="ItemNumber"]/text()')[0].extract().strip(), id1)
                    image_url = ''
                    tmp = hxs.select('//div[@id="ShotView"]//img/@src').extract()
                    if not tmp:
                        tmp = opt_sel.select('@data-imageurl').extract()
                    if tmp:
                        image_url = tmp[0]

                    name1 = ''
                    tmp = opt_sel.select('text()').extract()
                    if tmp:
                        name1 = tmp[0]
                    options2 = sel.select('.//div[@class="DropDown"][2]//option[@value!=""]')
                    if options2:
                        item = copy.deepcopy(product)
                        item['identifier'] = id1
                        item['name'] = '-'.join([name, name1])
                        item['image_url'] = image_url
                        item['price'] = price
                        item['sku'] = sku
                        if price:
                            item['stock'] = 1
                        else:
                            item['stock'] = 0
                        yield Request(url="http://www.next.co.uk/item/%s?CTRL=select" % id1.replace('-', '').lower(),
                                      meta={'item': item, 'rules': response.meta.get('rules'),
                                            'limit': response.meta.get('limit')},
                                      callback=self.parse_select)

                    else:
                        # Has only 1 level options
                        item = copy.deepcopy(product)
                        item['identifier'] = id1
                        item['name'] = '-'.join([name, name1])
                        item['image_url'] = image_url
                        item['price'] = price
                        item['sku'] = sku
                        if price:
                            item['stock'] = 1
                        else:
                            item['stock'] = 0
                        # yield item
                        if not item['identifier'] in self.id_seen:
                            self.id_seen.append(item['identifier'])
                            yield item
                            # self.cookie_num += 1
                            # yield FormRequest(url="http://www.next.co.uk/bag/add", formdata={'id':id1.replace('-',''), 'option':'01', 'quantity':'1'}, meta={'item':item, 'cookiejar':self.cookie_num}, dont_filter=True, callback=self.parse_price)

            elif sel.select('.//select[@name="Size"]/option'):
                item = copy.deepcopy(product)
                tmp = sel.select('.//div[@class="ItemNumber"]/text()').extract()
                if not tmp:
                    continue
                id1 = tmp[0]
                name = ''
                tmp = sel.select('.//div[@class="Title"]/*[self::h1 or self::h2]//text()').extract()
                if tmp:
                    name = ''.join([x for x in tmp]).strip()

                cat = self._select_category(name, response, cat)
                if cat:
                    item['category'] = ' > '.join(cat)
                price = 0
                tmp = sel.select('.//div[@class="Price"]/text()').extract()
                if tmp:
                    price = extract_price(tmp[0].strip())
                item['identifier'] = id1
                tmp = sel.select('.//section[@class="StyleImages"]//img/@src').extract()
                if tmp:
                    item['image_url'] = tmp[0]
                item['sku'] = id1
                item['name'] = name
                item['price'] = price

                yield Request(url="http://www.next.co.uk/item/%s?CTRL=select" % id1.replace('-', '').lower(),
                              meta={'item': item, 'rules': response.meta.get('rules'),
                                    'limit': response.meta.get('limit')},
                              callback=self.parse_select)

                continue

            else:  # no options
                if hxs.select('//select'):
                    log.msg("SELECT FOUND: %s %s" % (response.url, hxs.select('.//select[not(@name="Size")]/@name').extract()))
                item = copy.deepcopy(product)
                tmp = sel.select('.//div[@class="ItemNumber"]/text()').extract()
                if tmp:
                    item['identifier'] = tmp[0]
                    item['sku'] = tmp[0]
                else:
                    log.msg('### No product id found at ' + response.url, level=log.INFO)
                    continue
                item['name'] = name
                cat = self._select_category(name, response, cat)
                if cat:
                    item['category'] = ' > '.join(cat)
                # tmp = sel.select('.//div[@class="Price"]/text()').extract()
                # if tmp:
                #    price = extract_price(tmp[0].strip())
                #    item['price'] = price
                item['price'] = price
                if price:
                    item['stock'] = 1
                else:
                    item['stock'] = 0
                tmp = sel.select('.//section[@class="StyleImages"]//img/@src').extract()
                if tmp:
                    item['image_url'] = tmp[0]

                if not item['identifier'] in self.id_seen:
                    self.id_seen.append(item['identifier'])
                    yield item

    def parse_select(self, response):
        # inspect_response(response, self)
        # return
        hxs = HtmlXPathSelector(response)
        item = response.meta['item']
        options = hxs.select('//option[@value!=""]')
        if options:
            for sel in options:  # ##
                itemn = copy.deepcopy(item)
                tmp = sel.select('@value').extract()
                if tmp:
                    itemn['identifier'] += '-' + tmp[0]
                tmp = sel.select('@class').extract()
                if tmp and tmp[0] == 'InStock':
                    itemn['stock'] = 1
                else:
                    itemn['stock'] = 0
                tmp = sel.select('text()').extract()
                if tmp:
                    ss = tmp[0].split('-')
                    itemn['name'] += '-' + ss[0].strip()
                    if len(ss) > 1:
                        price = extract_price(ss[1].strip())
                        if price != 0:
                            itemn['price'] = price
                yield itemn
        else:
            yield item

    def parse_price(self, response):
        # inspect_response(response, self)
        # return
        item = response.meta['item']
        j = json.loads(response.body)
        d = j['Bag']['Items']
        if d:
            price = extract_price(d[0]['Price'])
            item['price'] = price
            if d[0]['StockStatus'] == 'instock':
                item['stock'] = 1
            else:
                item['stock'] = 0
        else:
            item['price'] = 0
            item['stock'] = 0

        return item


# -*- coding: utf-8 -*-

import os
import re
import itertools
import ast
import random
from copy import deepcopy
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.utils import extract_price

from scrapy import log

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)


HERE = os.path.abspath(os.path.dirname(__file__))


class RelaxSofasAndBeds(BaseSpider):
    name = "colourbank-relaxsofasandbeds.co.uk"
    allowed_domains = ["relaxsofasandbeds.co.uk"]
    start_urls = ["http://www.relaxsofasandbeds.co.uk"]

    def __init__(self, *args, **kwargs):
        self.current_cookie = 0
        self.user_agents = []

    def start_requests(self):
        with open(os.path.join(HERE, '../../useragents.txt')) as f:
            for l in f:
                user_agent = l.strip()
                if user_agent:
                    self.user_agents.append(user_agent)

        for url in self.start_urls:
            yield Request(url, headers={'User-Agent': random.choice(self.user_agents)})

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        category_urls = hxs.select('//div[@id="menu"]//li/a[not(contains(@href, "brands"))]/@href').extract()
        for url in category_urls:
            self.current_cookie += 1
            yield Request(urljoin(base_url, url),
                          headers={'User-Agent': random.choice(self.user_agents)},
                          meta={'cookiejar': self.current_cookie})

        product_urls = hxs.select('//div[@class="grid-item"]//h3/a/@href').extract()
        for url in product_urls:
            self.current_cookie += 1
            yield Request(urljoin(base_url, url),
                          callback=self.parse_product,
                          headers={'User-Agent': random.choice(self.user_agents)},
                          meta={'cookiejar': self.current_cookie})

        category_products = hxs.select('//div[@class="category-name"]/a/@href').extract()
        for url in category_products:
            self.current_cookie += 1
            yield Request(urljoin(base_url, url),
                          callback=self.parse_category_product,
                          headers={'User-Agent': random.choice(self.user_agents)},
                          meta={'cookiejar': self.current_cookie})

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//div[@class="item"]')
        if products:
            log.msg('CATEGORY PRODUCTS FOUND >>> ' + response.url)
            for item in self.parse_category_product(response):
                yield item
            return


        name = hxs.select('//div[@id="itemlist-moreinfo-title"]/h1/text()').extract()
        identifier = hxs.select('//input[@name="additems[]"]/@value').extract()
        identifier = identifier[0]
        if not identifier:
            identifier = hxs.select('//form/@id').re('item(\d+)')[0]




        price = hxs.select('//span[@id="price"]/text()').extract()
        price = extract_price(price[0])

        loader = ProductLoader(selector=hxs, item=Product())
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        image_url = hxs.select('//a[@id="big-image-popup"]/img/@src').extract()
        image_url = urljoin(base_url, image_url[0]) if image_url else ''
        loader.add_value('image_url', image_url)
        categories = hxs.select('//div[@id="breadcrumb-new"]/a/text()').extract()
        categories = categories[1:] if categories else ''
        loader.add_value('category', categories)
        loader.add_value('url', response.url)
        if loader.get_output_value('price')<=0:
            loader.add_value('stock', 0)

        product = loader.load_item()

        select_options = []
        html_comments = ''.join(re.findall('<!-- (.*) -->', ' '.join(response.body.split())))
        if "new Array([" not in html_comments:
            for l in response.body.split('\n'):
                for line in l.split(';'):
                    if "new Array([" in line:
                        option = ast.literal_eval(re.search(" new Array\((.*)\)", line).group(1))
                        if isinstance(option, tuple):
                            select_options.append(list(option))
                        else:
                            select_options.append([option])

        if select_options and len(select_options)<3:
            options = []
            if len(select_options)>1:
                combined_options = list(itertools.product(*select_options))
                for combined_option in combined_options:
                    final_option = {}
                    for option in combined_option:
                        final_option['desc'] = final_option.get('desc', '') + ' ' + option[1]
                        final_option['identifier'] = final_option.get('identifier', '') + '-' + option[0]
                        final_option['price'] = final_option.get('price', 0) + extract_price(option[2])
                    options.append(final_option)
            else:
                for option in select_options[0]:
                    final_option = {}
                    final_option['desc'] = ' ' + option[1]
                    final_option['identifier'] = '-' + option[0]
                    final_option['price'] = extract_price(option[2])
                    options.append(final_option)

            for option in options:
                option_product = deepcopy(product)
                option_product['identifier'] = option_product['identifier'] + option['identifier']
                option_product['name'] = option_product['name'] + option['desc']
                option_product['price'] =  option['price']
                option_product['sku'] = option_product['identifier']
                yield option_product
        else:
            yield product

        category_products = hxs.select('//div[@class="item"]')
        if category_products:
            log.msg('Category products found: ' + response.url)
            for item in self.category_products(response):
                yield item

    def parse_category_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//div[@id="breadcrumb-new"]/a/text()').extract()
        categories = categories[1:] if categories else ''

        products = hxs.select('//div[@class="item"]')
        for product in products:

            name = ' '.join(product.select('.//div[@class="item-title"]/span//text()').extract()).strip()
            identifier = product.select('.//input[@name="item_id"]/@value').extract()[0]

            price = product.select('.//span[contains(@id, "total-price-baseprice")]/text()').extract()
            price = extract_price(price[0])

            loader = ProductLoader(selector=hxs, item=Product())
            loader.add_value('name', name)
            loader.add_value('price', price)
            loader.add_value('identifier', identifier)
            loader.add_value('sku', identifier)
            image_url = product.select('.//div[@class="item-image"]//img/@src').extract()
            image_url = urljoin(base_url, image_url[0]) if image_url else ''
            loader.add_value('image_url', image_url)
            loader.add_value('category', categories)
            loader.add_value('url', response.url)
            if loader.get_output_value('price')<=0:
                loader.add_value('stock', 0)

            item = loader.load_item()

            yield item

            options_url = "http://www.relaxsofasandbeds.co.uk/load_options_2015.phtml"
            cat_id = product.select('.//input[@name="cat_id"]/@value').extract()[0]
            formdata = {'cat_id': cat_id, 'item_id':identifier}
            yield FormRequest(options_url,
                              dont_filter=True,
                              formdata=formdata,
                              callback=self.parse_product_options,
                              meta={'item': item,
                                    'cookiejar': response.meta['cookiejar']},
                              headers={'User-Agent': response.request.headers['User-Agent']})

    def parse_product_options(self, response):
        hxs = HtmlXPathSelector(response)
        item = response.meta['item']

        options = hxs.select('//table[contains(@id, "swatch-price-band-wrapper")]//td/div')
        for option in options:
            option_item = deepcopy(item)
            identifier = option.select('@id').re('-(\d+)')[0]
            option_item['identifier'] += '-' + identifier
            name = option.select('a/@title').re(' - (.*) <b>')
            if not name:
                name = option.select('a/@title').re('(.*) <b>')
            name = name[0]
            option_item['name'] += ' ' + name
            price = extract_price(option.select('a/@title').re('<b>(.*)</b>')[0])
            option_item['price'] += price
            if option_item['price'] > item['price']:
                yield option_item

# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from decimal import Decimal
from product_spiders.utils import fix_spaces
import re
import json
import itertools
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class BedSiteCoUK(BaseSpider):
    name = "bedsite.co.uk"
    allowed_domains = ["bedsite.co.uk"]
    start_urls = ["http://www.bedsite.co.uk/"]

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        category_urls = hxs.select('//div[contains(@class, "nav-block")]/ul[contains(@class, "level0")]/li[contains(@class, "nav-item")]/a/@href').extract()
        category_urls += hxs.select('//li[contains(@class,"level1")]/a/@href').extract()
        for url in category_urls:
            yield Request(url, callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        next_url = hxs.select('//div[@class="pages"]//a[@title="Next"]/@href').extract()
        if next_url:
            yield Request(next_url[0], callback=self.parse_category)

        product_urls = response.css('.product-name a::attr(href)').extract()
        for url in product_urls:
            yield Request(url, callback=self.parse_product)
            
    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(selector=hxs, item=Product())

        price = hxs.select('//div[contains(@class,"product-shop")]//span[contains(@id, "product-price")]//text()[normalize-space()]').extract()
        if price:
            stock = 1
        else:
            price = 0
            stock = 0
        category = hxs.select('//div[@class="breadcrumbs"]//li/a/span/text()').extract()
        del category[0]
        del category[:-3]
        sku = hxs.select('//div[@itemprop="description"]/ul/li[1]/text()').extract()
        if sku:
            sku = re.findall(r'Ref: +(\w+)', sku[0])
            
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        loader.add_value('price', price)
        loader.add_xpath('brand', '//meta[@itemprop="brand"]/@content')
        loader.add_value('sku', sku)
        loader.add_xpath('image_url', '//img[@id="image-main"]/@src')
        loader.add_value('url', response.url)
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_value('stock', stock)
        loader.add_value('category', category)

        product = loader.load_item()
        option_ids = hxs.select('//div[contains(@id, "product-options")]//li[@class="option"]/div[@is-required="1"]/span[@class="title"]/text()[not(contains(., "Headboard")) and not(contains(., "Footboard"))]/../../@type-id').extract()
        option_data = hxs.select('//script/text()').re("optionBook.options = JSON.parse\('(.+)'\)")
        if option_ids and option_data:
            for p in self.parse_options(product, option_ids, option_data):
                yield p
        else:
            yield product
            
    def parse_options(self, product, option_ids, option_data):
        options = json.loads(option_data[0])
        data = {}
        for idx in options.iterkeys():
            if idx in option_ids:
                data[idx] = options[idx]
        options = {}
        for idx in data.iterkeys():
            options[idx] = {}
            for idy in data[idx].iterkeys():
                if Decimal(data[idx][idy]['price']) != 0:
                    options[idx][idy] = data[idx][idy]
            if not options[idx]:
                del options[idx]
        variants = itertools.product(*(options[idx].values() for idx in options))
        for variant in variants:
            item = Product(product)
            for attr in variant:
                item['identifier'] += attr['attr_id']
                item['price'] += Decimal(attr['price'])
                item['name'] += ' ' + attr['name']
            yield item
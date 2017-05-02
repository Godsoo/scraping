# -*- coding: utf-8 -*-
"""
Customer: Specsavers NO
Website: https://www.yourlenses.no
Extract all products on site
"""

import re
import json
from copy import deepcopy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter
from urlparse import urljoin

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader



class YourLenses(BaseSpider):
    name = "specsavers_no-yourlenses.no"
    allowed_domains = ["yourlenses.no"]
    start_urls = ['https://www.yourlenses.no']

    def parse(self, response):
        base_url = get_base_url(response)

        categories = response.xpath('//ul[@id="nav-left"]//a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))
        
        products = response.xpath('//li[contains(@class, "content-product")]/a/@href').extract()
        for product in products:
            yield Request(urljoin(base_url, product), callback=self.parse_product)

        next = response.xpath('//div[contains(@class, "prodList-pagination")]/a[@title="neste"]/@href').extract()
        if next and products:
            yield Request(response.urljoin(next[0]))

    def parse_product(self, response):
        base_url = get_base_url(response)

        name = response.xpath('//div[@class="infotitle"]/h1/text()').extract()
        name = ' '.join(name)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name)
        loader.add_xpath('price', '//span[@class="inline price price"]/text()')
        image_url = response.xpath('//img[@class="photo"]/@src').extract()
        if image_url:
            loader.add_value('image_url', 'http:' + image_url[0])
        loader.add_xpath('brand', '//meta[@itemprop="brand"]/@content')
        loader.add_value('category', '')
        loader.add_value('url', response.url)
        identifier = response.xpath('//input[@name="prodid"]/@value').extract()[0]
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)

        item = loader.load_item()
        yield item
            

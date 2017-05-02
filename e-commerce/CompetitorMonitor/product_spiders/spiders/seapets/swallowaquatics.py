#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       Version 0.01
#       Started 09.08.2012
#       Autor   Roman <romis@wippies.fi>
import re

from scrapy import log
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url

from product_spiders.items import Product, ProductLoader


class SwallowaquaticsSpider(BaseSpider):
    name = 'swallowaquatics'
    allowed_domains = ['swallowaquatics.co.uk']
    start_urls = ['http://www.swallowaquatics.co.uk/']

    def parse(self, response): 
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        cats = hxs.select(
                "//div[@class='nav-container']/ul/li/a/@href").extract()
        if cats:
            #log.msg(">>>>>>>>>>>>>>>>>>>> CATEGORIES FOUND %s" % len(cats))
            for cat in cats:
                yield Request(
                        url=canonicalize_url(cat),
                        callback=self.parse_cat)

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        subcats = hxs.select("//div/ul/li/h2/a/@href").extract()
        if subcats:
            #log.msg(">>>>>>>>>>>>>>>>>>>> SUBCATEGORIES FOUND %s" % len(subcats))
            for subcat in subcats:
                yield Request(
                        url=canonicalize_url(subcat),
                        callback=self.parse_cat)

        next_page = hxs.select(
                ".//div[@class='pages']/ol/li"
                "/a[contains(@class,'next')]/@href").extract()
        if next_page:
            #log.msg(">>>>>>>>>>>>>>>>>>>> TURN TO NEXT PAGE")
            yield Request(
                    url=canonicalize_url(next_page[0]),
                    callback=self.parse_cat)

        products = hxs.select(".//ul/li[@class='item']/a/@href").extract()
        if products:
            #log.msg(">>>>>>>>>>>>>>>>>>>> ITEMS FOUND %s" % len(products))
            for product in products:
                yield Request(
                        url=canonicalize_url(product),
                        callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        url = response.url   
        name = ''.join(hxs.select(
                ".//div[@id='product-header']/div/h1/text()"
                ).extract()).strip()
        price = ''.join(hxs.select(
                ".//div[@id='product-header']/div/div/span"
                "/span[@class='price']/text()").extract()).strip()

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name)
        loader.add_value('url', url)
        loader.add_value('price', price)
        yield loader.load_item()
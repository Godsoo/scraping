# -*- coding: utf-8 -*-
import csv
import json
import os
import shutil
from datetime import datetime
import StringIO
import urlparse
import re
import hashlib
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import CloseSpider
from scrapy import signals

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader, ProductLoaderEU
from product_spiders.utils import extract_price_eu, extract_price


HERE = os.path.abspath(os.path.dirname(__file__))


class PurnimaDigitalSpider(BaseSpider):
    name = 'purnimadigital'
    allowed_domains = ['purnimadigital.com']
    start_urls = ['http://www.purnimadigital.com']

    products_regex = re.compile(r'''(http.*html)''')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # we extract the categories urls
        categories = hxs.select("//li[contains(concat('',@class,''), 'catlevel2')]/a/@href").extract()
        for category in categories:
            yield Request(
                category,
                callback=self.parse_category
            )

    def parse_category(self, response):
        """
        While parsing a category page we need to look after a product or category list
        """
        hxs = HtmlXPathSelector(response)

        # products
        for product_url in hxs.select("//div[contains(concat('',@id,''), 'lbg-trans')]/@onclick").extract():
            url = self.products_regex.findall(product_url)
            if url:
                yield Request(
                    url[0],
                    callback=self.parse_product
                )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)

        price = Decimal(0)
        price_script = ''.join(hxs.select("//script[contains(., 'productPrice')]/text()").extract())
        if price_script:
            price = re.findall(r'productPrice":(\d+)', price_script)
            if price:
                price = extract_price(price[0])
        else:
            price = ''.join(hxs.select(
                "//div[@id='product-simple']//span[contains(concat('',@id,''), 'product-price')]//text()").extract())
            price = ''.join(re.findall('([\d\.,]+)', price))
            price = extract_price_eu(price)

        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_xpath('name', "//h1/text()")
        if hxs.select("//p[@class='availability']/img[@alt='En stock']").extract():
            stock = '1'
        else:
            stock = '0'
        loader.add_value('stock', stock)
        loader.add_xpath('category', "//div[@class='breadcrumbs']//li[1< position()]//a/text()")
        loader.add_xpath('brand', "//table[@class='data-table']//tr[contains(., 'Marque')]/td/text()")
        loader.add_value('shipping_cost', "0")
        sku = ''.join(hxs.select("//input[@type='hidden' and @name='product']/@value").extract())
        loader.add_value('sku', sku.strip())
        loader.add_value('identifier', sku)
        loader.add_xpath('image_url', "//a[@class='MagicZoomPlus']/img/@src")
        yield loader.load_item()
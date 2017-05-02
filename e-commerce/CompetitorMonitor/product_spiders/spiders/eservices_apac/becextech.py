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


class BecexTechalSpider(BaseSpider):
    name = 'becextech'
    allowed_domains = ['becextech.co.nz']
    start_urls = [
        'http://www.becextech.co.nz',
        # 'http://www.becextech.co.nz/computer/-tablet-amazon-tablet-amazon-kindle-fire-hdx-16gb-wifi-tablet-p-4255.html',
        # 'http://www.becextech.co.nz/computer-tablet-amazon-tablet-c-24_102.html',
        # 'http://www.becextech.co.nz/camera-accessories-c-85.html',
        # 'http://www.becextech.co.nz/digital-still-cameras-nikon-digital-still-camera-c-22_34.html',
        # 'http://www.becextech.co.nz/digital-camera-lense-pro-lense-carl-zeiss-digital-camera-lenses-c-51_114.html',
    ]

    # a very strange website, xpath isn't always working for products and subcategories
    products_regex = re.compile(r'<div\s*class=\"lst\-det\-btn\"><a\s*href=\"(.*)\"><img')
    sub_category_regex = re.compile(r'<div\s*class=\"brand\-icon\"><a\s*href=\"(.*)\"><img')
    next_page_regex = re.compile(r'<div\s*class=\"first">.*<a\s*href=\"(.*)\"\s*class=""\s*title="\s*Next')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # we extract the categories urls
        categories = hxs.select("//div[@class='menu-cat']//a/@href").extract()
        for category in categories:
            yield Request(
                category,
                callback=self.parse_category
            )
        # yield Request(
        #     response.url,
        #     callback=self.parse_category,
        #     dont_filter=True,
        # )

    def parse_category(self, response):
        """
        While parsing a category page we need to look after a product or category list
        """
    #     tree = html.fromstring(response.body)
        hxs = HtmlXPathSelector(response)
        # sub categories
        for product_url in self.sub_category_regex.findall(response.body):
            yield Request(
                product_url,
                callback=self.parse_category
                # callback=self.parse
            )

        # products
        for product_url in self.products_regex.findall(response.body):
            yield Request(
                product_url,
                callback=self.parse_product
            )

        # products
        for product_url in hxs.select("//td[@class='productListing-data']//div[@class='pro-txt']//a[1]/@href").extract():
            yield Request(
                product_url,
                callback=self.parse_product
            )

        # next page
        # next_page_url_list = hxs.select("//a[@title=' Next Page ']/@href").extract()
        next_page_url_list = self.next_page_regex.findall(response.body)
        self.log(str(self.next_page_regex.findall(response.body)))
        if next_page_url_list:
            yield Request(
                next_page_url_list[-1],
                callback=self.parse_category
                # callback=self.parse
            )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)

        loader.add_xpath('price', "//div[@class='det-price']//span[@itemprop='price']/text()")
        loader.add_value('url', response.url)
        loader.add_xpath('name', "//span[@itemprop='name']//text()")
        if hxs.select("//div[@id='product_info']//text()[contains(., 'Out of Stock')]").extract():
            stock = '0'
        else:
            stock = '1'
        loader.add_value('stock', stock)
        loader.add_xpath('category', "//div[@class='headerNavigation']//a[2 < position() and position() < last()]//text()")
        loader.add_value('brand', "")
        loader.add_value('shipping_cost', "29.95")
        loader.add_xpath('sku', "//div[@class='det-buynow']//input[@name='products_id']/@value")
        loader.add_xpath('identifier', "//div[@class='det-buynow']//input[@name='products_id']/@value")
        image_url_l = hxs.select("//div[@class='img-top']//img/@src").extract()
        if image_url_l:
            image_url = urlparse.urljoin(base=get_base_url(response), url=image_url_l[0])
        else:
            image_url = ''
        loader.add_value('image_url', image_url)
        yield loader.load_item()

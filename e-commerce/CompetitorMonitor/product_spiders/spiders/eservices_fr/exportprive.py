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


class ExportPriveDigitalSpider(BaseSpider):
    name = 'exportprive.fr'
    allowed_domains = ['exportprive.fr']
    start_urls = ['http://www.exportprive.fr']

    product_id_regex = re.compile(r'''id_product\s*=\s*\'(\d*)\';''')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # we extract the categories urls
        categories = hxs.select("//a[@class=' title_col_cat']/@href").extract()
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
        for product_url in hxs.select("//a[@class='product_img_link']/@href").extract():
            yield Request(
                product_url,
                callback=self.parse_product
            )

        # next page
        next_page_url_list = hxs.select("//li[@class='pagination_next']/a/@href").extract()
        if next_page_url_list:
            yield Request(
                next_page_url_list[0],
                callback=self.parse_category
            )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)

        price = ''.join(hxs.select("//span[@id='our_price_display']//text()").extract())
        price = ','.join(re.findall('([\d\.,]+)', price))
        price = extract_price_eu(price)

        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_xpath('name', "//h1//text()")
        if hxs.select("//p[@id='stock_statut']//img[contains(./@src, 'stock_in.png')]").extract():
        # if price:
            stock = '1'
        else:
            stock = '0'
        loader.add_value('stock', stock)
        loader.add_xpath('category', "//div[@class='breadcrumb']/a[1 < position()]/text()")
        loader.add_xpath('brand', "//div[@id='block_link_manu']//p[contains(., 'Voir tous les produits')]//a/text()")
        loader.add_value('shipping_cost', "0")
        sku = ''.join(hxs.select("(//h2[@id='product_reference']//text())[2]").extract())
        loader.add_value('sku', sku.strip())

        script = ''.join(hxs.select("(//script[contains(., 'id_product')]//text())[1]").extract())
        product_id = self.product_id_regex.findall(script)

        loader.add_value('identifier', ''.join(product_id))
        loader.add_xpath('image_url', "//img[@id='bigpic']/@src")
        yield loader.load_item()
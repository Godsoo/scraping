# -*- coding: utf-8 -*-
import csv
import os
import shutil
from datetime import datetime
import StringIO
import urlparse
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import CloseSpider
from scrapy import signals

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class KuvaldasSpider(BaseSpider):
    name = 'kuvalda3.ru'
    allowed_domains = ['kuvalda.ru']
    start_urls = ['http://www.kuvalda.ru']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # we extract the categories urls
        categories = hxs.select("//ul[@class='catalogue-menu']//a/@href").extract()
        for category in categories:
            yield Request(
                urlparse.urljoin(response.url, category),
                callback=self.parse_categories
            )

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)

        # we extract the subcategories urls
        sub_cats = hxs.select("//h3[@class='catalogue-group-name']//a/@href").extract()
        for sub_cat in sub_cats:
            yield Request(
                urlparse.urljoin(response.url, sub_cat),
                callback=self.parse_subcategories
            )

    def parse_subcategories(self, response):
        hxs = HtmlXPathSelector(response)

        # extract sub_categories urls
        sub_cats = hxs.select("//h3[@class='catalogue-group-name']//a/@href").extract()
        for sub_cat in sub_cats:
            yield Request(
                urlparse.urljoin(response.url, sub_cat),
                callback=self.parse_subcategories
            )

        # extract the product urls
        products_href = hxs.select(
            "//div[@class='selection-placeholder']//a[contains(concat(' ',@class,' '), 'itemsline-itemimage')]/@href").extract()
        for href in products_href:
            url = urlparse.urljoin(get_base_url(response), href)
            yield Request(url, callback=self.parse_product)

        # extract next pages url
        next_page_href = hxs.select("//a[@class='page-next']/@href").extract()
        for nhref in next_page_href:
            url = urlparse.urljoin(get_base_url(response), nhref)
            yield Request(url, callback=self.parse_subcategories)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)

        if hxs.select("//dd[@class='product-id-code--value']").extract():
            # page example: http://www.kuvalda.ru/catalog/1952/36043/
            product_in_stock = hxs.select("//form[@class='product-order js-order']").extract()
            if product_in_stock:
                stock = '1'
            else:
                stock = '0'
            price = ''.join([x.strip() for x in
                             hxs.select("(//div[@class='product-info-online--price'])[1]/text()").extract()]).replace('.', '').replace(',', '.')
            loader.add_value('price', price)
            loader.add_value('url', response.url)
            loader.add_xpath('identifier', "//dd[@class='product-id-code--value']//text()")
            loader.add_xpath('name', '//h1//text()')
            # loader.add_xpath('currency', '//div[@class="hproduct"]/div/div/h1[@class="title"]/strong/text()')
            loader.add_value('stock', stock)
            loader.add_xpath('category', "(//ul[@class='breadcrumbs']//a)[position() > 2]//text()")
            loader.add_xpath('brand', "//dd[@class='product-id-brand--value']//img/@alt")
            loader.add_value('shipping_cost', '0.0')
            loader.add_xpath('sku', "//dd[@class='product-id-code--value']//text()")
            loader.add_xpath('image_url', "(//div[@class='product-gallery']//img/@src)[1]")
        else:
            # page example: http://www.kuvalda.ru/catalog/4322/12064/
            product_in_stock = hxs.select("//form[@data-price]/@data-price").extract()
            if product_in_stock:
                # price = product_in_stock[0]
                stock = '1'
            else:
                stock = '0'
            price = ''.join(hxs.select(
                "(//div[contains(concat(' ',@class,' '), 'price')])[1]//text()[not(ancestor::span[@class='unit'])]").extract()).replace('.', '').replace(',', '.')
            loader.add_value('price', price.strip())
            loader.add_value('url', response.url)

            loader.add_xpath('name', '//h1//text()')
            # loader.add_xpath('currency', '//div[@class="hproduct"]/div/div/h1[@class="title"]/strong/text()')
            loader.add_value('stock', stock)
            loader.add_xpath('category', '//div[@class="body-col2-crumbs"]/a[position() > 2]//text()')
            loader.add_xpath('brand', "//a[@class='firm']//text()")
            loader.add_value('shipping_cost', '0.0')
            sku = ''.join(hxs.select("//div[@class='body-col2-item-rightcol-art']/text()[1]").extract())
            sku = re.findall(r'(\d+)', sku)[0]
            loader.add_value('identifier', sku)
            loader.add_value('sku', sku)
            loader.add_xpath('image_url', "(//a[@rel='lightbox']/img/@src)[1]")
        yield loader.load_item()
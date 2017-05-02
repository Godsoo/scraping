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
from lxml import html

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


class GerryBibbsCameraWarehouseSpider(BaseSpider):
    name = 'gerrygibbscamerawarehouse'
    allowed_domains = ['gerrygibbscamerawarehouse.com.au', ]
    start_urls = [
        'http://gerrygibbscamerawarehouse.com.au',
        ]

    products_regex = re.compile(r'''(?s)var\s+products_json\s*=\s*(\{.*?\});''')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # we extract the categories urls
        categories = hxs.select("//a[contains(concat('',@class,''), 'category-top')]/@href").extract()
        for category in categories:
            yield Request(
                urlparse.urljoin(response.url, category),
                callback=self.parse_category
            )

    def parse_category(self, response):
        """
        While parsing a category page we need to look after a product or category list
        """
        tree = html.fromstring(response.body)
        hxs = HtmlXPathSelector(response)

        # if the page is a product
        # product_page = hxs.select("//div[@id='cartAdd']").extract()
        product_page = tree.xpath("//div[@id='productDescription']//text()")
        if product_page:
            yield Request(
                response.url,
                callback=self.parse_product,
                dont_filter=True
            )

        # products
        for product_url in hxs.select("//a[img[@class='listingProductImage']]/@href").extract():
            yield Request(
                product_url,
                callback=self.parse_product
            )

        # sub categories
        for category_url in hxs.select("//div[@class='categoryListBoxContents']/a/@href").extract():
            yield Request(
                category_url,
                callback=self.parse_category
            )

        # next page
        next_page_url_list = hxs.select("//a[@title=' Next Page ']/@href").extract()
        if next_page_url_list:
            yield Request(
                next_page_url_list[0],
                callback=self.parse_category
            )

    def parse_product(self, response):
        tree = html.fromstring(response.body)
        loader = ProductLoader(item=Product(), response=response)

        price = tree.xpath("//h2//span[@class='productSpecialPrice']/text()")
        if not price:
            price = tree.xpath("//h2[@id='productPrices']/text()[last()]")

        loader.add_value('price', price)
        loader.add_value('url', response.url)
        product_name = ''.join(tree.xpath("//div[contains(concat('',@class,''), 'name-type')]//text()"))

        loader.add_value('name', product_name)
        loader.add_value('stock', '1')
        loader.add_value('category', ''.join(tree.xpath("//h1[@id='productName']//text()")))
        brand_str = ''.join(tree.xpath("//form[@name='cart_quantity']//li[contains(., 'Manufactured')]//text()"))
        brand = brand_str.split(':')[-1]
        loader.add_value('brand', brand.strip())
        loader.add_value('shipping_cost', "17.95")
        sku_script = ''.join(tree.xpath("//form[@name='cart_quantity']//li[contains(., 'Model')]//text()"))
        sku = sku_script.split(':')[-1]
        loader.add_value('sku', sku.strip())
        loader.add_value('identifier', ''.join(tree.xpath("//div[@class='currencies']//input[@name='products_id']/@value")))

        image_src = ''.join(tree.xpath("//div[@id='productMainImage']//img/@src"))
        image_url = urlparse.urljoin(get_base_url(response), image_src)
        loader.add_value('image_url', image_url)

        metadata = {}

        for option in tree.xpath("//h4[contains(concat('',@class,''), 'optionName')]"):
            choices = option.xpath("./following-sibling::div//text()")
            cleaned_choices = [x for x in choices if x.strip()]
            option_name = ''.join(option.xpath(".//text()"))
            metadata[option_name] = cleaned_choices

        loader.add_value("metadata", metadata)

        return loader.load_item()
# -*- coding: utf-8 -*-

import os

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from scrapy.spider import BaseSpider

from product_spiders.config import DATA_DIR
import pandas as pd

HERE = os.path.abspath(os.path.dirname(__file__))


class CosmoMusicSpider(BaseSpider):
    name = 'cosmomusic'
    allowed_domains = ['cosmomusic.ca']
    start_urls = ['http://cosmomusic.ca/']

    rotate_agent = True

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # we extract the categories urls
        category_selector = \
            "//li[contains(concat('',@class,''), 'level0')][position() < 3]//li[contains(concat('',@class,''), 'level2')]/a/@href"
        category_selector = '//ol[@class="nav-primary"]//a/@href'
        categories = hxs.select(category_selector).extract()
        for category in categories:
            self.log("category: {}".format(category))
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
        products = hxs.select('//div[@class="category-products"]/ul/li')
        for product in products:
            product_url = product.select('.//h2[@class="product-name"]/a/@href').extract()
            if product_url:
                product_url = product_url[0]
                self.log("product: {} scraped from {}".format(product_url, response.url))
                yield Request(product_url, callback=self.parse_product)

        # next page
        next_page_url_list = hxs.select("//a[contains(concat('', @class,''), 'next')]/@href").extract()
        if next_page_url_list:
            self.log("next page url: {}".format(next_page_url_list[0]))
            yield Request(
                next_page_url_list[0],
                callback=self.parse_category
            )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        price = filter(lambda p: p.strip(), hxs.select("//span[@class='regular-price']//text()").extract())[1:]

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_xpath('name', "//div[@class='product-name']//h1//text()")
        loader.add_xpath('category', "//div[@class='breadcrumbs']//li[position() > 1 and position() < last()]/a/text()")
        brand = hxs.select("//div[@class='product-shop']/div[@class='product-name']/a[@class='brand']/text()").extract()
        loader.add_value('brand', brand)
        loader.add_value('shipping_cost', 0)
        loader.add_xpath('sku', '//li/span[text()="SKU:"]/../text()')
        loader.add_xpath('identifier', "//div[@class='product-view']//input[@name='product']/@value")
        image_urls = hxs.select('//img[contains(@class, "gallery-image")]/@src').extract()
        for image_url in image_urls:
            if len(image_url) < 1024:
                loader.add_value('image_url', image_url)
                break
        product = loader.load_item()
        if product['price'] > 0:
            yield product

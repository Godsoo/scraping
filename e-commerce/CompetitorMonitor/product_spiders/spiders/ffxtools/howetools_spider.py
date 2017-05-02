# -*- coding: utf-8 -*-
import os
import re

from scrapy import log

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from utils import extract_price


from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class HoweToolsSpider(BaseSpider):
    name = 'ffxtools-howetools.co.uk'
    allowed_domains = ['howetools.co.uk']
    start_urls = ['https://www.howetools.co.uk/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//li[contains(@class, "level0")]/a/@href').extract()
        categories += hxs.select('//li[@class="amshopby-advanced"]/ol//a/@href').extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            yield Request(url)

        products =  hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, callback=self.parse_product)

        next = hxs.select('//a[contains(@class, "i-next")]/@href').extract()
        if next:
            next = urljoin_rfc(get_base_url(response), next[0])
            yield Request(next)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//meta[@property="og:title"]/@content')
        loader.add_value('url', response.url)

        product_brand = ''
        brands = hxs.select('//dl[dt/text()="Brand"]//li/@data-text').extract()
        for brand in brands:
            if brand.upper() in loader.get_output_value('name').upper():
                product_brand = brand
                break

        loader.add_value('brand', product_brand)
        categories = hxs.select('//div[@class="breadcrumbs"]//li[not(@class="home")]/a/text()').extract()
        loader.add_value('category', categories)
        identifier = hxs.select('//input[@name="product"]/@value').extract()
        loader.add_value('sku', identifier)
        loader.add_value('identifier', identifier)
        image_url = hxs.select('//img[@class="big"]/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])

        price = hxs.select('//div[@class="product-shop"]//span[@class="price-including-tax"]//span[@class="price"]/text()').extract()
        price = extract_price(price[0]) if price else 0
 
        loader.add_value('price', price)

        out_of_stock = hxs.select('//p[@class="availability out-of-stock"]')
        if out_of_stock or not loader.get_output_value('price'):
            loader.add_value('stock', 0)
       
        yield loader.load_item()

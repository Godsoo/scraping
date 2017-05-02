# -*- coding: utf-8 -*-
import os
import urlparse
import re
import hashlib
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import url_query_parameter

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price


HERE = os.path.abspath(os.path.dirname(__file__))


class RhinoCameraSpider(BaseSpider):

    name = 'eservices_sw-rhinocamera.se'
    allowed_domains = ['rhinocamera.se']
    start_urls = ['http://rhinocamera.se']


    def parse(self, response):

        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//ul[@id="nav-main"]/li/a')
        for category in categories:
            url = category.select('@href').extract()[0]
            category_name = category.select('text()').extract()[0]
            yield Request(urlparse.urljoin(response.url, url), meta={'category': category_name})

        products = hxs.select('//a[@class="productnamecolour"]/@href').extract()
        for product_url in products:
            yield Request(urlparse.urljoin(get_base_url(response), product_url), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        brands = set(hxs.select('//div[p[contains(span/text(), "Via m")]]/ul/li/a/text()').extract())

        loader = ProductLoader(item=Product(), response=response)

        price = hxs.select('//p[contains(@class, "final-price")]/span[@class="bold"]/text()').extract()[0]
        price = extract_price(price)

        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/span/text()')

        loader.add_value('category', response.meta['category'])
        brand = ''
        for b in brands:
            if loader.get_output_value('name').upper().startswith(b.upper()):
                brand = b
                break

        loader.add_value('brand', brand)

        identifier = url_query_parameter(response.url, "ProductID")
        loader.add_value('sku', identifier)
        loader.add_value('identifier', identifier)
        image_url = hxs.select('//a[@id="Zoomer"]//img/@src').extract() 
        image_url = urlparse.urljoin(get_base_url(response), image_url[0]) if image_url else ''
        loader.add_value('image_url', image_url)

        yield loader.load_item()

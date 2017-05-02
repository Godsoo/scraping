# -*- coding: utf-8 -*-

"""
Account: SpecSavers NL

Extract all contact lenses.
"""

import json
import re

from scrapy.spider import BaseSpider
from scrapy.http import Request

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class SpecSavers(BaseSpider):
    name = 'specsavers_nl-specsavers.nl'
    allowed_domains = ['specsavers.nl']

    start_urls = ('https://www.specsavers.nl/contactlenzen/shop',)

    def parse(self, response):
        for url in response.xpath('//a[contains(@class,"product-tile")]/@href').extract():
            yield Request(response.urljoin(url), callback=self.parse_product)

    def parse_product(self, response):
        product = re.findall('"products":(.*)}}}', response.body)
        if product:
            product = json.loads(product[0])[0]

            loader = ProductLoader(item=Product(), response=response)
            name = response.xpath('//div[contains(@class,"field-name-title")]/h1/text()').extract()
            name += response.xpath('//div[contains(@class,"field-name-field-cl-lens-type")]/div/span/text()').extract()
            name += response.xpath('//div[contains(@class,"form-item-cl-supply")]/text()').extract()
            loader.add_value('name', u' '.join([x.strip() for x in name]))
            loader.add_value('identifier', response.url.split('/')[-1])
            loader.add_value('url', response.url)
            loader.add_value('brand', product['brand'])
            loader.add_value('category', product['category'])
            image_url = response.xpath('//img[contains(@class, "img-responsive")]/@src').extract()
            if image_url:
                loader.add_value('image_url', image_url)
            loader.add_value('price', product['price'])

            yield loader.load_item()

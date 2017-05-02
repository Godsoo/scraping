# -*- coding: utf-8 -*-
"""
Account: BetterLife HealthCare
Name: betterlife_healthcare-completecareshop.co.uk
Original developer: Franco Almonacid <fmacr85@gmail.com>
"""

import re
from copy import deepcopy

from scrapy import Spider
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price


class CompleteCareShopSpider(Spider):
    name = u'betterlife_healthcare-completecareshop.co.uk'
    allowed_domains = ['completecareshop.co.uk']
    start_urls = ['https://www.completecareshop.co.uk/']

    def parse(self, response):
        base_url = get_base_url(response)
        categories = response.xpath('//div[@id="mainNavigation"]//a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url))

        products = response.xpath('//a[contains(@onclick, "clickProduct")]/@href').extract()
        if products:
            for url in products:
                yield Request(response.urljoin(url), callback=self.parse_product)

    def parse_product(self, response):
        options = response.xpath('//div[@id="newProdOptions"]//option[not(@value="0")]/@value').extract()
        for option in options:
            yield Request(response.urljoin(option), callback=self.parse_product)

        identifier = response.xpath('//input[@name="productID"]/@value').extract()[0]
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        name = response.xpath('//h1[@itemprop="name"]/text()').extract()[0].strip()
        sku = response.xpath('//strong[@itemprop="sku"]/text()').extract_first()
        price = response.xpath('//div[contains(@class, "ppBPrice")]//span[contains(@class, "ppBPCurPrice")]/text()').extract()[0].strip()
        categories = response.xpath('//div[@id="breadcrumb"]//a/span/text()').extract()[1:-1]

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('identifier', identifier)
        product_loader.add_value('name', name)
        if image_url:
            product_loader.add_value('image_url', response.urljoin(image_url[0]))
        product_loader.add_value('sku', sku)
        product_loader.add_value('price', price)
        product_loader.add_value('url', response.url)
        product_loader.add_value('category', categories)
        product_loader.add_value('brand', '')
        yield product_loader.load_item()

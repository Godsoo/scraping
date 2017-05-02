# -*- coding: utf-8 -*-
"""
Customer: Specsavers IE
Website: http://www.eurolens.ie
Extract all products on site

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4554-specsavers-ie---new-site---eurolens/details#

"""

import urlparse
import os

from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price


class EurolensSpider(BaseSpider):
    name = 'specsavers_ie-eurolens.ie'
    allowed_domains = ['eurolens.ie']
    start_urls = ['http://www.eurolens.ie/contactsatoz.asp']


    def parse(self, response):
        # categories and subcategories
        categories = response.xpath('//div[@id="allproducts"]/ul[@class="atozjump"]/li/a[not(contains(@href, "#"))]/@href').extract()
        for cat_href in categories:
            yield Request(urlparse.urljoin(get_base_url(response), cat_href))


        # products
        products = response.xpath('//ul[contains(@class, "productList")]//li/a/@href').extract()
        products += response.xpath('//a[@class="productName"]/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product)

    def parse_product(self, response):
        url = response.url

        products = response.xpath('//ul[contains(@class, "productList")]//li/a/@href').extract()
        products += response.xpath('//a[@class="productName"]/@href').extract()
        if products:
            for url in products:
                yield Request(response.urljoin(url), callback=self.parse_product)
            return

        l = ProductLoader(item=Product(), response=response)

        name = response.xpath('//div[@id="heading"]/h1/text()').extract()[0].strip()
        l.add_value('name', name)


        price = response.xpath('//tr[th[contains(text(), "Regular")]]/td//text()').re('\d+.\d+')
        if not price:
            price = response.xpath('//ul[@id="pricing-details"]//span[@class="price"]/text()').extract()
        if not price:
            price = response.xpath('//ul[@id="pricing-details"]//li[@class="em"]/text()').extract()

        price = price[0] if price else ''
        price = extract_price(price)
        l.add_value('price', price)

        identifier = response.xpath('//input[@name="prodid"]/@value').extract()[0]
        l.add_value('identifier', identifier)
        brand = response.xpath('//tr[th[contains(text(), "Manufac")]]/td//text()').extract()
        if not brand:
            brand = response.xpath('//div[@id="VPUPPManufacturer"]/text()').re('by (.*)')
        l.add_value('brand', brand)
        categories = response.xpath('//div[@id="breadcrumbs"]//a/text()').extract()
        l.add_value('category', categories)
        image_url = response.xpath('//div[@id="productimage"]/img/@src').extract()
        if not image_url:
            image_url = response.xpath('//div[@id="product-image"]//div[contains(@id, "productimage")]/img/@src').extract()
        if image_url:
            l.add_value('image_url', image_url)
        l.add_value('url', url)

        stock = response.xpath('//div[@id="product-availability"]/p[contains(text(), "In stock")]')
        if not stock:
            l.add_value('stock', 0)


        product = l.load_item()


        yield product

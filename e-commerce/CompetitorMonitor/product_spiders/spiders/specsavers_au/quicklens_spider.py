# -*- coding: utf-8 -*-
"""
Customer: Specsavers AU
Website: http://www.quicklens.com.au/
Extract all products on site

https://www.assembla.com/spaces/competitormonitor/tickets/4564-specsavers-nz--amp--au-|-quicklens-|-new-spider/details#

"""
import re
import urlparse
import os

from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price


class QuicklensSpider(BaseSpider):
    name = 'specsavers_au-quicklens.com.au'
    allowed_domains = ['quicklens.com.au']
    start_urls = ['http://www.quicklens.com.au/index/list/']


    def parse(self, response):
        # products
        products = response.xpath('//div[@id="lmenu_goodslist"]//a/@href').extract()
        products += response.xpath('//div[contains(@class, "list_allproducts")]//a/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product)

    def parse(self, response):
        # products
        products = response.xpath('//div[@id="lmenu_goodslist"]//a/@href').extract()
        products += response.xpath('//div[contains(@class, "list_allproducts")]//a/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product)

    def parse_product(self, response):
        url = response.url

        l = ProductLoader(item=Product(), response=response)

        name = response.xpath('//table[@id="goods"]//td/h1/text()').extract()[0].strip()
        l.add_value('name', name)


        price = response.xpath('//table[@id="goods"]//td/strong[@class="price" and not(contains(text(), "box"))]/text()').extract()
        price = extract_price(price[0]) if price else ''
        l.add_value('price', price)

        identifier = response.xpath('//input[@name="gc"]/@value').extract()[0]
        l.add_value('identifier', identifier)
        l.add_value('sku', identifier)

        brand = response.xpath('//li[b[contains(text(), "Manufacturer")]]/text()').extract()
        if not brand:
            brand = re.findall('Manufacturer:</b>(.*).<br', response.body)
        if not brand:
            brand = response.xpath('//tr[td/strong/text()="Manufacturer"]/following-sibling::tr/td/h2/text()').extract()
        brand = brand[0].strip() if brand else ''
        l.add_value('brand', brand)

        l.add_value('shipping_cost', 9.50)

        categories = response.xpath('//li[b[contains(text(), "Type")]]/text()').extract()
        if not categories:
            categories = re.findall('Type:</b>(.*).<br', response.body)
        if not categories:
            categories = response.xpath('//tr[td/strong/text()="Lens Type"]/following-sibling::tr[1]/td[2]/text()').extract()
        categories = categories[0].strip().replace('.', '') if categories else ''
        l.add_value('category', categories)

        image_url = response.xpath('//meta[@property="og:image"]/@content').extract()
        if image_url:
            l.add_value('image_url', image_url)
        l.add_value('url', url)

        yield l.load_item()

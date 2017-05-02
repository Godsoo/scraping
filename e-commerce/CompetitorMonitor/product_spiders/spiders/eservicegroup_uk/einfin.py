# -*- coding: utf-8 -*-
"""
Account: E-Service UK
Name: eservices_uk-e-infin.com
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4608-e-services-uk---new-site---e-infin/details#
Original developer: Franco Almonacid <fmacr85@gmail.com>
"""

import re
import json
from scrapy import Spider
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price


class EInfinSpider(Spider):
    name = u'eservices_uk-e-infin.com'
    allowed_domains = ['e-infin.com']
    start_urls = ['http://www.e-infin.com/uk/']

    def parse(self, response):
        base_url = get_base_url(response)

        categories = response.xpath('//div[@id="category"]//a/@href').extract()
        categories += response.xpath('//div[@class="title"]/a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url))

        product_list = response.xpath('//script[contains(@src, "itemlist")]/@src').extract()
        if product_list:
            yield Request(response.urljoin(product_list[0]), callback=self.parse_product_list)

        products = response.xpath('//div[contains(@class, "swipe_item_containe")]/a/@href').extract()
        for product in products:
            identifier = re.findall('item\/(\d+)\/', product)
            yield Request(response.urljoin(product), callback=self.parse_product, meta={'identifier': identifier})

    def parse_product_list(self, response):
        data = re.findall('var items = (.*);var paraFields', response.body)
        if data:
            product_url = 'http://www.e-infin.com/uk/item/%s/%s'
            products = json.loads(data[0])
            for product in products:
                yield Request(product_url % (product[0], product[1].replace(' ', '_')), callback=self.parse_product, meta={'identifier': product[0]})

    def parse_product(self, response):
        base_url = get_base_url(response)

        identifier = response.meta['identifier']
        image_url = response.xpath('//div[@id="gallery"]/img/@src').extract()
        brand = response.xpath('//div[@itemprop="brand"]/text()').extract()[0]
        name = ' '.join(response.xpath('//div[@itemprop="name"]//text()').extract()).strip()
        categories = response.xpath('//div[contains(@class, "breadcrumb")]//a/text()').extract()[1:]


        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('identifier', response.meta['identifier'])
        product_loader.add_value('sku', response.meta['identifier'])
        product_loader.add_value('name', brand + ' ' + name)
        if image_url:
            product_loader.add_value('image_url', response.urljoin(image_url[0]))
        product_loader.add_xpath('price', '//span[@itemprop="price"]/text()')
        product_loader.add_value('url', response.url)

        product_loader.add_value('category', categories)
        product_loader.add_value('brand', brand)
        in_stock = response.xpath('//div[@itemprop="availability" and @content="in_stock"]')
        if not in_stock:
            product_loader.add_value('stock', 0)
        product = product_loader.load_item()
        yield product

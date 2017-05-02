# -*- coding: utf-8 -*-
"""
Customer: Powerhouse Fitness
Website: http://www.fitness-superstore.co.uk
Extract all products on site, including product options

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4584-powerhouse-fitness-|-superstore-|-new-spider/details#

"""

import re

from datetime import datetime
from scrapy.spider import BaseSpider
from scrapy.http import Request
from copy import deepcopy

from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import (Product, ProductLoaderWithNameStrip as ProductLoader)
from scrapy.contrib.loader.processor import MapCompose, Join, TakeFirst, Identity
from scrapy.contrib.loader import XPathItemLoader
from scrapy.utils.markup import remove_entities
from product_spiders.utils import extract_price
import logging


class ArgosCoUKKeterSpider(BaseSpider):
    name = 'powerhouse_fitness-fitness-superstore.co.uk'
    allowed_domains = ['fitness-superstore.co.uk']
    start_urls = ['http://www.fitness-superstore.co.uk/']
    
    custom_settings = {'COOKIES_ENABLED': False}

    def parse(self, response):
        categories = response.xpath('//ul[@id="nav"]//a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url))

        sub_categories = response.xpath('//div[contains(@class, "sub-cat-block")]/a/@href').extract()
        for url in sub_categories:
            yield Request(response.urljoin(url))

        pages = response.xpath('//div[@class="pages"]//li/a/@href').extract()
        for url in pages:
            yield Request(response.urljoin(url))

        products = response.xpath('//div[@class="product-item__name"]//a/@href').extract()
        if products:
            category_names = response.xpath('//div[@class="breadcrumbs"]//li/a/text()').extract()
            category_names += response.xpath('//div[@class="breadcrumbs"]//li/strong/text()').extract()
            category_names = ' > '.join(category_names[1:])
            for url in products:
                yield Request(response.urljoin(url), callback=self.parse_product, meta={'category': category_names})

        identifier = response.xpath('//input[@id="entity_id"]/@value').extract()
        if identifier:
            for product in self.parse_product(response):
                yield product

    def parse_product(self, response):
        url = response.url

        l = ProductLoader(item=Product(), response=response)

        name = response.xpath('//span[@itemprop="name"]/text()').extract()
        try:
            name = name[0].strip()
        except IndexError:
            retry = response.meta.get('retry', 0)
            if retry <= 3:
                yield Request(response.url, dont_filter=True, callback=self.parse_product, meta={'retry': retry + 1})

        l.add_value('name', name)

        price = response.xpath('//p[@class="special-price"]/span[@class="price"]/text()').extract()
        if price:
            price = price[0]
        else:
            price = response.xpath('//span[@class="regular-price"]/span[@class="price"]/text()').extract()
            if price:
                price = price[0]
        l.add_value('price', price)

        sku = response.xpath('//div[@class="product-shop--sku"]/h4/span/text()').extract()
        l.add_value('sku', sku[0])
        
        identifier = response.css('div.nosto_product span.product_id::text').extract() or response.xpath('//input[@id="entity_id"]/@value').extract()
        l.add_value('identifier', identifier[0])

        l.add_value('category', response.meta.get('category', ''))

        image_url = response.xpath('//span[@class="image_url"]/text()').extract()
        l.add_value('image_url', image_url)
        l.add_value('url', url)
        l.add_xpath('brand', '//span[@class="brand"]/text()')
 
        out_of_stock = response.xpath('//div[contains(@class, "availability-box")]/p[contains(@class, "out-of-stock")]')
        if out_of_stock:
            l.add_value('stock', 0)

        item = l.load_item()

        options = response.xpath('//table[@id="super-product-table"]/tbody/tr')
        if options:
            for option in options:
                option_item = deepcopy(item)
                option_item['name'] = option.xpath('td[1]/text()').extract()[0]
                price = option.xpath('td//span[@class="price"]/text()').extract()
                price = extract_price(price[0]) if price else 0
                option_item['price'] = price
                identifier = option.xpath('td//input/@name').re('\[(.*)\]')
                if not identifier:
                    identifier = option.xpath('td//span/@id').re('product-price-(.*)')
                    option_item['stock'] = 0

                option_item['identifier'] += '-' + identifier[0]
                yield option_item
        else:
            yield item



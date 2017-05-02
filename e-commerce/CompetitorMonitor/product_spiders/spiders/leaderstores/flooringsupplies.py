# -*- coding: utf-8 -*-
"""
Customer: Leader Stores
Website: http://www.leaderdoors.co.uk
Extract all products, including options.

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4480-leader-stores---new-site---flooring-supplies

"""
import re
import collections
import os
from copy import deepcopy
from decimal import Decimal
import json
import itertools
import urllib
from urlparse import urljoin as urljoin_rfc

from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter
from scrapy.http import Request


from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class FlooringSuppliesSpider(BaseSpider):
    name = 'leaderstores-flooringsupplies.co.uk'
    allowed_domains = ['flooringsupplies.co.uk']
    start_urls = ('http://www.flooringsupplies.co.uk/',)

    def parse(self, response):
        categories = response.xpath('//section[@id="menuBar"]//a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))

        products = response.xpath('//section[@id="productListing"]//a[div[p[@class="title"]]]/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product)

        next_pages = response.xpath('//ul[@class="pagination"]//a[@rel="next"]/@href').extract()
        for next_page in next_pages:
            yield Request(response.urljoin(next_page))

    def parse_product(self, response):
        price = response.xpath('//tr[th[contains(text(),"Price per Pack")]]//span[@class="incVAT"]/text()').extract()
        if not price:
            price = response.xpath('//tr[contains(@class,"mainPrice")]//span[contains(@class,"incVAT")]/em/text()').extract()
        if not price:
            price = response.xpath('//tr[contains(@class,"price")]//span[contains(@class,"incVAT")]/em/text()').extract()
        categories = response.xpath('//nav[@class="breadcrumbs"]/a/text()')[1:-1].extract()
        brand = response.xpath('//meta[@itemprop="brand"]/@content').extract()
        sku = response.xpath('//td[@itemprop="identifier"]/text()').extract()
        sku = sku[0].strip() if sku else ''
        #identifier = response.xpath('//td[@itemprop="identifier"]/text()').extract()

        identifier = response.url.split('/')[-2]
        image_url = response.xpath('//a[@data-lightbox="product"]/img/@src').extract()
        if image_url:
            image_url = response.urljoin(image_url[0])
        name = response.xpath('//h1[@itemprop="name"]/text()').extract()
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', sku)
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        processed_price = loader.get_output_value('price')
        self.log(repr(processed_price))
        if processed_price and Decimal(processed_price) < Decimal('175.00'):
            loader.add_value('shipping_cost', Decimal('15.00'))
        if image_url:
            loader.add_value('image_url', image_url)
        stock = response.xpath('//li[@itemprop="availability"]/@content').extract()
        if stock and stock[0] != 'in_stock':
            loader.add_value('stock', 0)
        for category in categories:
            loader.add_value('category', category)
        loader.add_value('brand', brand)
        options = response.xpath('//select[@name="ddlProductOptions"]/option')
        if not options:
            yield loader.load_item()
            return
        for opt in options:
            opt_name = opt.xpath('./text()')[0].extract()
            loader.replace_value('name', '{} {}'.format(name[0], opt_name))
            opt_value = opt.xpath('./@value')[0].extract()
            opt_id = response.xpath('//tr[contains(@class,"option_{}")]'
                                    '//td[@itemprop="identifier"]/text()'.format(opt_value)).extract()
            loader.replace_value('identifier', opt_value)
            loader.replace_value('sku', opt_value)
            opt_price = response.xpath('//tr[(contains(@class,"price") or contains(@class,"mainPrice"))'
                                       ' and contains(@class,"option_{}")]'
                                       '//span[contains(@class,"incVAT")]/em/text()'.format(opt_value)).extract()
            loader.replace_value('price', opt_price)
            if Decimal(loader.get_output_value('price')) < Decimal('175.00'):
                loader.add_value('shipping_cost', Decimal('15.00'))
            else:
                loader.add_value('shipping_cost', Decimal('0.00'))
            opt_stock = response.xpath('//ul[contains(@class,"option_{}")]'
                                       '/li[@itemprop="availability"]/@content'.format(opt_value)).extract()
            if opt_stock and opt_stock[0] != 'in_stock':
                loader.add_value('stock', 0)
            else:
                loader.add_value('stock', 1)
            yield loader.load_item()

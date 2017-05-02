# -*- coding: utf-8 -*-
"""
Customer: Leader Stores
Website: http://www.ncsfloorsdirect.co.uk
Extract all products, including options.

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4478--leader-stores---new-site---ncs-floors-direct

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
try:
    from scrapy.selector import Selector
except ImportError:
    from scrapy.selector import HtmlXPathSelector as Selector
from scrapy.http import Request


from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class NCSFlooringSpider(BaseSpider):
    name = 'leaderstores-ncsflooring.co.uk'
    allowed_domains = ['ncsflooring.co.uk']
    start_urls = ('http://www.ncsflooring.co.uk/',)

    def parse(self, response):

        categories = response.xpath('//div[@id="categoriescss"]//a/@href').extract()
        categories += response.xpath('//a[@class="category_row"]/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))

        products = response.xpath('//a[@class="product_name"]/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product)

        next_page = response.xpath('//div[@class="listing_links"]//a[contains(text(),"View All")]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]))

    def parse_product(self, response):
        sel = Selector(response)
        price = sel.re(re.compile('jsProductPrice = \'(.*)\';'))
        categories = sel.xpath('//div[@id="navBreadCrumb"]/a/text()')[1:].extract()
        brand = sel.xpath('//span[@class="product_manufacturer"]/text()').re('Manufactured by: (.*)')
        brand = brand[0].strip() if brand else ''
        sku = sel.xpath('//span[@class="product_model"]/text()').re('Ref: (.*)')
        sku = sku[0].strip() if sku else ''
        identifier = re.search('p-(.*)\.html', response.url).group(1)
        image_url = response.xpath('//div[@id="replace_image_zoom"]//img[@class="zoom_pic"]/@src').extract()
        if image_url:
            image_url = response.urljoin(image_url[0])
        name = sel.xpath('//h1[@class="productGeneral"]/text()').extract()
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', sku)
        loader.add_value('name', name)
        loader.add_value('price', price)
        price = loader.get_output_value('price')
        if price and Decimal(price) < Decimal('400.0'):
            loader.add_value('shipping_cost', Decimal('35.00'))
        loader.add_value('url', response.url)
        if image_url:
            loader.add_value('image_url', image_url)
        for category in categories:
            loader.add_value('category', category)
        loader.add_value('brand', brand)
        yield loader.load_item()
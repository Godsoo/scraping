# -*- coding: utf-8 -*-
"""
Customer: Red Hot Sunglasses
Website: http://redhotsunglasses.co.uk
Extract products from feed

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4790

"""

import csv
import os
import re 
import json
from copy import deepcopy

from scrapy.spider import BaseSpider
from scrapy.http import Request
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


from scrapy.selector import XmlXPathSelector

from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from scrapy import Item, Field

HERE = os.path.abspath(os.path.dirname(__file__))

class RHSMeta(Item):
    cost_price = Field()

class RedHotSunglassesSpider(BaseSpider):
    name = 'redhotsunglasses-redhotsunglasses.co.uk'
    allowed_domains = ['redhotsunglasses.co.uk']
    start_urls = ['http://redhotsunglasses.co.uk/googleproducts/GETXML']
    product_ids = []
    monitored_products = {}

    def start_requests(self):
        self.log(os.path.join(HERE, 'rhs_monitored_products.csv'))
        self.log(os.path.exists(os.path.join(HERE, 'rhs_monitored_products.csv')))
        with open(os.path.join(HERE, 'rhs_monitored_products.csv')) as f:
            self.monitored_products = csv.DictReader(f)
            self.monitored_products = {row['Model Number'].upper().strip(): row for row in self.monitored_products}

        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):

        xxs = XmlXPathSelector(response)
        xxs.remove_namespaces()
        products = xxs.select('//item')
        for product in products:
            mpn = product.xpath('mpn/text()')
            if mpn:
                mpn = mpn[0].extract().upper().strip()
            else:
                mpn = None
            row = self.monitored_products.get(mpn) if mpn else None
            if row is None or (row and row['Discontinued'].lower().strip() == 'yes'):
                continue
            loader = ProductLoader(selector=product, item=Product())
            loader.add_xpath('identifier', 'id/text()')
            loader.add_xpath('sku', 'mpn/text()')
            loader.add_xpath('brand', 'brand/text()')
            loader.add_xpath('image_url', 'image_link/text()')
            loader.add_xpath('url', 'link/text()')
            loader.add_xpath('name', 'title/text()')
            price = product.select('sale_price/text()').extract()
            if not price:
                price = product.select('price/text()').extract()

            loader.add_value('price', extract_price(price[0]))

            categories = product.select('product_type/text()').extract()[-1].split('>')
            categories = map(lambda x: x.strip(), categories)
            loader.add_value('category', categories)

            shipping_cost = product.select('shipping/price/text()').extract()
            shipping_cost = extract_price(shipping_cost[0]) if shipping_cost else ''
            loader.add_value('shipping_cost', shipping_cost)

            in_stock = product.select('availability[contains(text(), "in stock")]').extract()
            if not in_stock:
                loader.add_value('price', 0)

            item = loader.load_item()
            item['metadata'] = RHSMeta()
            item['metadata']['cost_price'] = row['Cost Price']
            yield item




# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url

import json
import os
import re
import csv

from cStringIO import StringIO

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

from scrapy.item import Item, Field


class SpecMeta(Item):
    lens_type = Field()


class SpecSavers(BaseSpider):
    name = 'specsavers_ie-specsavers.ie'
    allowed_domains = ['specsavers.ie']

    filename = os.path.join(HERE, 'specsavers.csv')
    start_urls = ('file://' + filename,)

    price_field = 'IE Price'
    
    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            identifier = row.get('ID', None)
            brand = row['Supplier'].decode('utf-8')
            name = row['lens-name'].decode('utf-8')

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('identifier', identifier)
            loader.add_value('url', '')
            loader.add_value('brand', brand)
            loader.add_value('category', brand)
            loader.add_value('price', row[self.price_field])
            p = loader.load_item()

            yield p

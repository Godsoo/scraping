# -*- coding: utf-8 -*-
"""
Customer: Leader Stores
Website: http://www.leaderfloors.co.uk
Extract all items from the feed

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4482-leader-stores---new-site---leader-floors

"""

import collections
import os
from copy import deepcopy
from decimal import Decimal
import json
import itertools
import urllib
from urlparse import urljoin as urljoin_rfc
import re

from scrapy.http import Request
from scrapy.spiders import XMLFeedSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter
try:
    from scrapy.selector import Selector
except ImportError:
    from scrapy.selector import HtmlXPathSelector as Selector

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class LeaderFloorsSpider(XMLFeedSpider):
    name = 'leaderstores-leaderfloors.co.uk'
    allowed_domains = ['leaderfloors.co.uk']
    start_urls = ('https://www.leaderfloors.co.uk/googleproducts/getXML',)
    itertag = 'item'

    def parse_node(self, response, node):
        loader = ProductLoader(item=Product(), selector=node)
        size = node.xpath('./*[local-name()="size"]/text()').extract()
        color = node.xpath('./*[local-name()="color"]/text()').extract()
        material = node.xpath('./*[local-name()="material"]/text()').extract()
        name = node.xpath('./*[local-name()="parent_title"]/text()').extract()
        if not name:
            name = node.xpath('./title/text()').extract()
        name = name[0]
        if material:
            name += u' {}'.format(material[0])
        if color:
            name += u' {}'.format(color[0])
        if size:
            name += u' {}'.format(size[0])
        loader.add_value('name', name)
        loader.add_xpath('url', './link/text()')
        loader.add_xpath('image_url', './*[local-name()="image_link"]/text()')
        loader.add_xpath('identifier', './*[local-name()="id"]/text()')
        loader.add_xpath('price', './*[local-name()="price"]/text()')
        loader.add_xpath('shipping_cost', './*[local-name()="shipping"]/*[local-name()="price"]/text()')
        loader.add_xpath('brand', './*[local-name()="brand"]/text()')
        loader.add_xpath('category', './*[local-name()="google_product_category"]/text()')
        loader.add_xpath('sku', './*[local-name()="mpn"]/text()')
        stock = node.xpath('./*[local-name()="availability"]/text()').extract()
        if stock and stock[0] == 'out of stock':
            loader.add_value('stock', 0)

        yield loader.load_item()

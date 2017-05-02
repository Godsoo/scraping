# -*- coding: utf-8 -*-
import os
import re
import csv
from copy import deepcopy
from urlparse import urljoin

from product_spiders.items import Product

from urlparse import urlparse
from urlparse import urljoin as urljoin_rfc
from urlparse import parse_qs

from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url

#from product_spiders.base_spiders.amazonspider import BaseAmazonSpider, filter_name

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider

from product_spiders.base_spiders.legoamazon import (
    check_price_valid,
)

HERE = os.path.abspath(os.path.dirname(__file__))

from scrapy import log

class EAAmazonSpider(BaseAmazonSpider):
    name = 'electronicarts-uk-amazon.co.uk-direct'
    all_sellers = False

    collect_products_from_list = False

    _use_amazon_identifier = True

    amazon_direct = True

    do_retry = True
    max_retry_count = 5

    domain = 'amazon.co.uk'

    collect_reviews = False
    reviews_once_per_product_without_dealer = False

    user_agent = 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36'

    def get_search_query_generator(self):
        with open(os.path.join(HERE, 'EAMatches.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Amazon Search']!="No match":
                    s_item = {
                            'sku': row['sku'],
                            'brand': '',
                            'name': '',
                            'category': '',
                            'price': 0,
                            }
                    yield (row['Amazon Search'], s_item)

    def match(self, meta, search_item, found_item):
        return True

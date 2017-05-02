# -*- coding: utf-8 -*-
"""
Customer: Speciality Commerce US
Website: http://www.amazon.com
Crawling process: search by brand using the last crawl for the spider client. 
Options: extract all options
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4069-specialty-commerce-us---amazon-spider/details#

IMPORTANT! this spider searches by brand on a specific sub-category, 
for this search_node is set as 702381011.
"""

import os
import csv

from scrapy import log

from scrapy.http import Request

from scrapy.selector import HtmlXPathSelector
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider, AmazonUrlCreator


class AmazonMarketplaceSpider(BaseAmazonSpider):
    name = 'specialitycommerceus-amazon-marketplace'
    domain = 'www.amazon.com'
    do_retry = True

    collect_new_products = True
    collect_used_products = False
    all_sellers = True
    try_suggested = False
    collect_products_with_no_dealer = False

    parse_options = True
    
    # Sub-category: Hair Replacement Wigs
    search_node = '702381011'


    second_code_list = {}

    def get_search_query_generator(self):
        brands = []
        with open(os.path.join(HERE, 'specialitycommerceus_products.csv')) as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                brand = row['brand'].upper().strip()
                if  brand not in brands:
                    brands.append(brand)

        for brand in brands:
            yield (brand,
                  {'sku': '',
                   'name': '',
                   'category':'',
                   'price': '',
                  })

    def match(self, meta, search_item, found_item):
        return True

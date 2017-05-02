# -*- coding: utf-8 -*-
"""
Customer: Luminox USA
Website: http://www.amazon.com
Crawling process: search by brand Luminox and then apply the brand filter 'Luminox'. 

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4518-luminox-us-and-uk-|-amazon-us-and-uk-|-new-sites/details#

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
    name = 'luminox_us-amazon-marketplace'
    domain = 'www.amazon.com'
    type = 'category'
    do_retry = True

    collect_new_products = True
    collect_used_products = False
    all_sellers = True
    try_suggested = False
    model_as_sku = True
    collect_products_from_list = False
    collect_products_with_no_dealer = False


    def get_category_url_generator(self):
        urls = [
            {'url': 'http://www.amazon.com/s/ref=sr_nr_p_89_0?fst=as%3Aoff&rh=i%3Aaps%2Ck%3ALuminox%2Cp_89%3ALuminox&keywords=Luminox&ie=UTF8&qid=1456254542&rnid=2528832011',
             'category': [u'Luminox']}
        ]
        for url in urls:
            yield (url['url'], url['category'])

    def match(self, meta, search_item, found_item):
        return True

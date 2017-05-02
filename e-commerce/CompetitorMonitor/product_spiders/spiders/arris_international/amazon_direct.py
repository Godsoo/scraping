# -*- coding: utf-8 -*-
"""
Arris International account
Amazon spider, extracts reviews with author and author location, renamed to reviewer.
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5554
"""
import os.path

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider


HERE = os.path.abspath(os.path.dirname(__file__))


class AmazonDirectSpider(BaseAmazonSpider):
    name = "arris_international-amazon.com_direct"
    domain = "amazon.com"

    type = ['search']
    amazon_direct = True

    parse_options = False
    collect_products_with_no_dealer = True

    try_suggested = False

    max_pages = 1
    model_as_sku = True

    reviews_only_matched = False
    collect_products_from_list = False
    collect_reviews = True
    reviews_collect_author = True
    reviews_collect_author_location = True

    def get_search_query_generator(self):
        skus = ['SB6141', 'SB6183', 'SB6190', 'SBG6400', 'SBG6580', 'SBG6700', 'SBG6900', 'SBG7580', 'SBR AC1200P',
                'SBR AC1900P', 'SBR AC3200P', 'SBX AC1200P', 'SBX 1000P']
        brand = 'SurfBoard'
        category = 'Electronics'

        for sku in skus:
            item = {
                'sku': sku,
                'brand': brand,
                'category': category
            }
            search_query = brand.lower() + ' ' + sku.lower()
            yield search_query, item

    def match(self, meta, search_item, found_item):
        return True

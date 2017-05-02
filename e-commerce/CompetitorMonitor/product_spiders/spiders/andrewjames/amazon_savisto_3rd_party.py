# -*- coding: utf-8 -*-
"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4721

The spider uses amazon base spider, search type, searching for "Savisto",
extracting all and only 3rd party prices (not amazon).
Collect reviews only from verified purchase

"""
import os

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider

HERE = os.path.abspath(os.path.dirname(__file__))



class BaseAndrewJamesAmazonCoUkSpider(BaseAmazonSpider):
    domain = 'amazon.co.uk'

    type = 'search'
    all_sellers = True
    exclude_sellers = ['Amazon']
    fulfilled_by_amazon_to_identifier = True

    _use_amazon_identifier = True

    parse_options = True

    collect_reviews = True
    reviews_only_verified = True
    reviews_only_matched = False

    do_retry = True
    model_as_sku = True

    max_pages = None

    brands = []

    def get_search_query_generator(self):
        for brand in self.brands:
            yield (brand, {})

    def match(self, meta, search_item, found_item):
        return True


class AndrewJamesAmazonCoUkSavisto3rdParth(BaseAndrewJamesAmazonCoUkSpider):
    name = 'andrewjames_amazon.co.uk_savisto_3rdparty'

    brands = ['Savisto']

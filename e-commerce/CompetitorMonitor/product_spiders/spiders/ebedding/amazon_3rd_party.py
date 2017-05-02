# -*- coding: utf-8 -*-
"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4944

The spider uses amazon base spider, search type, searching for EANs from feed file "feed_for_amazon.csv",
extracting all and only 3rd party prices (not amazon).

"""
import os.path
import csv

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class EbeddingAmazonCoUkSpider3rdParty(BaseAmazonSpider):
    name = 'ebedding-amazon.co.uk-3rd_party'
    domain = 'amazon.co.uk'

    type = 'search'
    all_sellers = True

    _use_amazon_identifier = True

    try_suggested = False

    def get_search_query_generator(self):
        with open(os.path.join(HERE, 'feed_for_amazon.csv')) as f:
            for row in csv.DictReader(f):
                yield (row['EAN'], {'sku': row['EAN']})

    def match(self, meta, search_item, found_item):
        return True

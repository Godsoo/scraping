# -*- coding: utf-8 -*-
"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4882

The spider uses amazon base spider, asins type.

"""
import os
import csv
import paramiko

from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider

HERE = os.path.abspath(os.path.dirname(__file__))



class BushIndustriesAmazonSpider(BaseAmazonSpider):
    domain = 'amazon.com'

    name = 'bushindustries-amazon.com'

    type = 'asins'
    all_sellers = True
    fulfilled_by_amazon_to_identifier = True

    _use_amazon_identifier = True

    parse_options = True

    collect_reviews = True
    reviews_only_verified = False
    reviews_only_matched = False

    do_retry = True
    max_pages = None

    brands = []

    file_path = HERE + '/bush_industries_flat_file.csv'

    def get_asins_generator(self):
        with open(self.file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['ASIN'].strip():
                    yield (row['ASIN'], row['ASIN'])

    def match(self, meta, search_item, found_item):
        return True

    """
    def construct_product(self, item, meta=None, use_seller_id_in_identifier=None):
        r = super(BushIndustriesAmazonSpider, self).construct_product(item, meta, use_seller_id_in_identifier)

        if self.type == 'asins':
            metadata = r.get('metadata', None)
            if not metadata:
                r['metadata'] = {
                    'asin': item['asin'],
                }
            else:
                r['metadata']['asin'] = item['asin']

        return r
    """

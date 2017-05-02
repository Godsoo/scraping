# -*- coding: utf-8 -*-
import csv
import os.path

from product_spiders.base_spiders.amazonspider2.amazonspider_concurrent import BaseAmazonConcurrentSpider


HERE = os.path.abspath(os.path.dirname(__file__))


class AmazonSpider(BaseAmazonConcurrentSpider):
    name = 'householdessentials-amazon.com-direct'
    domain = 'amazon.com'

    type = 'search'

    amazon_direct = True
    collect_new_products = True
    collect_used_products = False
    _use_amazon_identifier = True
    collected_identifiers = set()
    collect_products_from_list = True

    collect_reviews = True
    review_date_format = None

    try_suggested = False
    do_retry = True
    rotate_agent = True

    root = HERE
    file_path = os.path.join(root, 'householdessentials_products.csv')

    def get_search_query_generator(self):
        with open(self.file_path) as f:
            reader = csv.DictReader(f, delimiter=',')
            for row in reader:
                asin = row['Amazon ASIN']
                if asin != '#N/A':
                    product = {'brand': row.get('Brand', ''),
                               'category': row.get('Brand', ''),
                               'sku': row['Item Number']}

                    yield asin, product

    def match(self, meta, search_item, found_item):
        return True

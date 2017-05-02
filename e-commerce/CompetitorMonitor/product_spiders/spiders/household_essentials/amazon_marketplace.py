# -*- coding: utf-8 -*-
import csv
import os.path

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class AmazonSpider(BaseAmazonSpider):
    name = 'householdessentials-amazon.com-marketplace'
    domain = 'amazon.com'

    type = 'asins_offers'

    all_sellers = True
    collect_new_products = True
    collect_used_products = False
    _use_amazon_identifier = True
    collected_identifiers = set()
    collect_products_from_list = True
    exclude_sellers = ['Amazon']

    collect_reviews = False
    review_date_format = None

    try_suggested = False
    do_retry = True
    rotate_agent = True

    retry_vendor_name = False

    root = HERE
    file_path = os.path.join(root, 'householdessentials_products.csv')

    def get_asins_generator(self):
        with open(self.file_path) as f:
            reader = csv.DictReader(f, delimiter=',')
            for row in reader:
                asin = row['Amazon ASIN']
                if asin != '#N/A':
                    product = {'brand': row.get('Brand', ''),
                               'category': row.get('Brand'),
                               'sku': row['Item Number']}

                    yield asin, product

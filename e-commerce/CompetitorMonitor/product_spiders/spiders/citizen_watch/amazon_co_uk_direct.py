import os
import csv

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class CitizenAmazonDirectSpider(BaseAmazonSpider):
    name = 'citizen-amazon.co.uk-direct'
    domain = 'www.amazon.co.uk'

    max_pages = 1
    do_retry = True
    retry_sleep = 10
    collect_new_products = True
    collect_used_products = False
    amazon_direct = True
    try_match_product_details_if_product_list_not_matches = True

    def __init__(self, *args, **kwargs):
        super(CitizenAmazonDirectSpider, self).__init__(*args, **kwargs)
        self.try_suggested = False

    def get_search_query_generator(self):
        with open(os.path.join(HERE, 'citizenproducts.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                s_item = {
                    'name': row['NAME'],
                    'sku': row['SKU'],
                    'price': row['RRP'],
                }

                yield ('citizen ' + row['SKU'], s_item)

    def match(self, meta, search_item, found_item):
        return search_item['sku'].lower() in found_item['name'].lower()

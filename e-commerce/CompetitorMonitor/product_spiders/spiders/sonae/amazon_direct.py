# -*- coding: utf-8 -*-
import csv
import os.path
from datetime import datetime
from product_spiders.base_spiders.amazonspider2.amazonspider_concurrent import BaseAmazonConcurrentSpiderWithCaptcha


HERE = os.path.abspath(os.path.dirname(__file__))


class AmazonSpider(BaseAmazonConcurrentSpiderWithCaptcha):
    name = 'sonae-amazon.es-direct'
    domain = 'amazon.es'

    type = 'search'

    amazon_direct = True
    collect_new_products = True
    collect_used_products = False
    _use_amazon_identifier = True
    collected_identifiers = set()
    collect_products_from_list = True

    collect_reviews = False
    scrape_categories_from_product_details = True

    try_suggested = False
    do_retry = True
    retry_sleep = 5
    

    rotate_agent = True

    root = HERE
    file_path = os.path.join(root, 'worten_products.csv')

    def __init__(self, *args, **kwargs):
        super(AmazonSpider, self).__init__(*args, **kwargs)

        if datetime.now().day == 5:
            self.use_previous_crawl_cache = False

    def get_search_query_generator(self):
        with open(self.file_path) as f:
            reader = csv.DictReader(f, delimiter=',')
            for row in reader:
                product = {'sku': row['sku']}

                yield row['sku'], product

    def match(self, meta, search_item, found_item):
        return True

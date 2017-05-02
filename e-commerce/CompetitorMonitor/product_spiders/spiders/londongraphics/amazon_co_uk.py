# coding=utf-8
__author__ = 'lucas'

import os.path
import paramiko
import csv
import datetime

from scrapy.http.request import Request
from scrapy.exceptions import CloseSpider

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider, AmazonUrlCreator

HERE = os.path.abspath(os.path.dirname(__file__))

class LondonGraphicsAmazonSpider(BaseAmazonSpider):
    name = 'london_graphics_amazon'
    allowed_domains = ['amazon.co.uk']
    exclude_sellers = ['LONDON GRAPHIC CENTRE']
    lowest_product_and_seller = True
    scrape_categories_from_product_details = True

    do_retry = True
    domain = 'amazon.co.uk'

    def __init__(self, *args, **kwargs):
        super(LondonGraphicsAmazonSpider, self).__init__(*args, **kwargs)

        file_path = HERE + '/asin.csv'

        with open(file_path) as f:
            reader = csv.DictReader(f)

            self.rows = list(reader)
            self.log("ASINs found: %d" % len(self.rows))

        self.errors.append("Spider works incorrectly: it should collect 'lowest seller', but that's not implemented")

    def get_search_query_generator(self):
        for i, row in enumerate(self.rows):
            yield ('', {'asin': row['asin'], 'sku': row['sku']})

    def get_next_search_request(self, callback=None):
        """
        Creates search request using self.search_generator
        """
        if not self.search_generator:
            return []
        try:
            search_string, search_item = next(self.search_generator)
        except StopIteration:
            return []

        self.log('Checking product [%s]' % search_item['asin'])

        self.current_search = search_string
        self.current_search_item = search_item
        self.collected_items = []
        self.processed_items = False

        requests = []
        url = AmazonUrlCreator.build_url_from_asin(self.domain, search_item['asin'])

        if callback is None:
            callback = self.parse_product

        requests.append(Request(url, meta={'search_string': search_string, 'search_item': search_item},
                        dont_filter=True, callback=callback))

        return requests

    def match(self, meta, search_item, found_item):
        return True

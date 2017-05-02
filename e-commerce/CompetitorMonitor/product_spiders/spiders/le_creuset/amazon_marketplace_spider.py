import os
import csv

from scrapy.http import Request

from scrapy.selector import HtmlXPathSelector
from product_spiders.utils import extract_price

from lecreusetitems import LeCreusetMeta

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider, AmazonUrlCreator


class LeCreusetAmazonBuyboxSpider(BaseAmazonSpider):
    name = 'lecreuset-amazon.co.uk-marketplace'
    domain = 'www.amazon.co.uk'
    max_pages = 1
    do_retry = True
    retry_sleep = 10
    collect_new_products = True
    collect_used_products = False
    all_sellers = True
    try_suggested = False
    collect_products_with_no_dealer = False

    exclude_sellers = ['Amazon']

    second_code_list = {}

    def __init__(self, *args, **kwargs):
        super(LeCreusetAmazonBuyboxSpider, self).__init__(*args, **kwargs)
        self.try_suggested = False
        self.current_searches = []

    def get_search_query_generator(self):
        with open(os.path.join(HERE, 'lecreuset_products.csv')) as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                search_term = row['Barcode'] if row['use_barcode'] == 'true' else row['SKU']
                yield (search_term,
                      {'sku': row['SKU'],
                       'name': '',
                       'category':'',
                       'price': '',
                      })

    def match(self, meta, search_item, found_item):
        return True

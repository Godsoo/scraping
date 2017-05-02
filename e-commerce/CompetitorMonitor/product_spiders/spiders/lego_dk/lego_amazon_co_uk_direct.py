# -*- coding: utf-8 -*-
import os
import csv
from decimal import Decimal

from product_spiders.utils import extract_price
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.exceptions import CloseSpider, DontCloseSpider

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.base_spiders.amazonspider2 import BaseLegoAmazonSpider
from product_spiders.base_spiders.amazonspider2.legoamazonspider import (
    name_fuzzy_match,
    sku_match,
    name_fuzzy_score,
    name_fuzzy_partial_score,
    check_price_valid,
    brand_match,
    filter_category,
)

class LegoAmazonSpider(BaseLegoAmazonSpider):
    name = 'legodk-amazon.co.uk-direct'
    lego_amazon_domain = 'www.amazon.co.uk'

    _use_amazon_identifier = True
    amazon_direct = True

    f_skus_found = os.path.join(HERE, 'amazon_direct_skus.txt')

    skus_found = []
    errors = []

    user_agent = 'spd'
    exchange_rate = 1

    def convert_to_pounds(self, price):
        return round(extract_price(price) / self.exchange_rate, 2)  # 1 pound = 8.88 DKK

    def get_search_query_generator(self):
        with open(os.path.join(HERE, 'legodk_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield (
                    'LEGO ' + row['Product No.'],
                    {
                        'sku': row['Product No.'],
                        'name': row['Item Description English'],
                        'category': row['Theme'],
                        'price': self.convert_to_pounds(row['RRP price DKK']),
                    }
                )

    def match(self, meta, search_item, new_item):
        import logging
        logging.error("===================================================")
        logging.error(search_item)
        logging.error(new_item)
        logging.error(self.match_lego_name(search_item, new_item))

        name = filter_category(new_item['name'], search_item['category'])
        logging.error("Filterer name: %s" % name)

        brand_matches = brand_match(new_item)
        name_matches = name_fuzzy_match(search_item['name'], name)
        sku_matches = sku_match(search_item, new_item)
        score = name_fuzzy_score(search_item['name'], name)
        partial_score = name_fuzzy_partial_score(search_item['name'], name)

        search_price = search_item.get('price')
        if search_price:
            price_matches = check_price_valid(search_price, new_item['price'])
            price_matches_soft = check_price_valid(search_price, new_item['price'], min_ratio=0.4, max_ratio=9)
        else:
            price_matches = True
            price_matches_soft = True

        product_matches = False
        if sku_matches and price_matches_soft:
            product_matches = True
        elif score >= 80 and price_matches_soft:
            product_matches = True
        elif partial_score >= 90 and price_matches:
            product_matches = True
        elif score >= 60 and price_matches:
            product_matches = True

        logging.error("Brand matches: %s" % brand_matches)
        logging.error("Matches: %s" % name_matches)
        logging.error("SKU Matches: %s" % sku_matches)
        logging.error("Match score: %s" % score)
        logging.error("Match partial score: %s" % partial_score)
        logging.error("Match price: %s" % price_matches)
        logging.error("Match price soft: %s" % price_matches_soft)
        logging.error("Product matches: %s" % product_matches)
        logging.error("===================================================")

        return brand_matches \
            and product_matches  \
            and not self.match_text('mini figures from', new_item) \
            and not self.match_text('mini figures only', new_item) \
            and not self.match_text('from set', new_item) \
            and not self.match_text('from sets', new_item)

    def start_requests(self):
        yield Request('http://www.xe.com/currencyconverter/convert/?Amount=1&From=GBP&To=DKK', callback=self.start_amazon_requests)

    def start_amazon_requests(self, response):
        """
        The method assumes the spider is using search.
        To get items to search spider must have `get_search_query_generator` function implemented, which must be
        generator returning tuple of form (search_string, search_item). This is not finally decided yet
        """
        hxs = HtmlXPathSelector(response)
        exchange_rate = hxs.select('//span[@class="uccResultAmount"]//text()').re('[\d\.]+')[0]

        self.exchange_rate = extract_price(exchange_rate)
        if self.type == 'search':
            self.search_generator = self.get_search_query_generator()
            requests = self.get_next_search_request()
            if not requests:
                raise CloseSpider("No search queries to process. Quitting")
        elif self.type == 'asins':
            self.asins_generator = self.get_asins_generator()
            requests = self.get_next_asin_request()
            if not requests:
                raise CloseSpider("No asins to process. Quitting")
        elif self.type == 'category':
            self.category_url_generator = self.get_category_url_generator()
            requests = self.get_next_category_request()
            if not requests:
                raise CloseSpider("No categories to process. Quitting")
        else:
            raise CloseSpider("Wrong spider type: %s" % self.type)

        return requests

    def transform_price(self, price):
        try:
            price = extract_price(price)
        except:
            price = price
        return price * self.exchange_rate
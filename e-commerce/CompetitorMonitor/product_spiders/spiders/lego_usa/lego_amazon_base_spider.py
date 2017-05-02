# -*- coding: utf-8 -*-
import os
import csv

from product_spiders.utils import extract_price

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
    minifigures_words
)

class BaseLegoAmazonUSASpider(BaseLegoAmazonSpider):
    lego_amazon_domain = 'www.amazon.com'

    def __init__(self, *args, **kwargs):
        super(BaseLegoAmazonUSASpider, self).__init__(*args, **kwargs)

        self.rows = []

        with open(os.path.join(HERE, 'lego.csv')) as f:
            reader = csv.reader(f)
            self.rows = list(reader)

    def get_search_query_generator(self):
        for i, row in enumerate(self.rows):
            yield (
                'LEGO ' + row[2],
                {
                    'sku': row[2],
                    'name': row[3].decode('utf-8'),
                    'category': row[1].decode('utf-8'),
                    'price': extract_price(row[4]),
                }
            )

    def basic_match(self, meta, search_item, new_item):
        return self.match_lego_name(search_item, new_item)

    def match(self, meta, search_item, new_item):
        # to mimic behaviour of old spider
        if not self.match_lego_name(search_item, new_item):
            return False
        name = filter_category(new_item['name'], search_item['category'])

        brand_matches = brand_match(new_item)
        name_matches = name_fuzzy_match(search_item['name'], name)
        sku_matches = sku_match(search_item, new_item)

        score = name_fuzzy_score(search_item['name'], name)
        partial_score = name_fuzzy_partial_score(search_item['name'], name)

        search_price = search_item.get('price')
        if search_price:
            if isinstance(new_item['price'], tuple):
                price_matches = any([check_price_valid(search_price, x) for x in new_item['price']])
                price_matches_soft = \
                    any([check_price_valid(search_price, x, min_ratio=0.4, max_ratio=9) for x in new_item['price']])
            else:
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

        contains_excluded_words = any([self.match_text(x, new_item) for x in minifigures_words])

        return brand_matches \
            and product_matches  \
            and not contains_excluded_words \
            and super(BaseLegoAmazonUSASpider, self).match(meta, search_item, new_item)

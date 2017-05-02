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


class LegoAmazonSpider(BaseLegoAmazonSpider):
    name = 'legouk-amazon.co.uk-direct'
    lego_amazon_domain = 'www.amazon.co.uk'
    # all_sellers = False
    _use_amazon_identifier = True
    # sellers = ['Amazon']
    amazon_direct = True

    f_skus_found = os.path.join(HERE, 'amazon_direct_skus.txt')

    skus_found = []
    errors = []

    user_agent = 'spd'

    def get_search_query_generator(self):
        with open(os.path.join(HERE, 'lego.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # if row['sku'] not in ('75001',): continue
                yield (
                    'LEGO ' + row['sku'],
                    {
                        'sku': row['sku'],
                        'name': row['name'],
                        'category': row['category'],
                        'price': extract_price(row['price']),
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
            self.log("[[TESTING]] Search price: %s" % str(search_price))
            self.log("[[TESTING]] Item price: %s" % str(new_item['price']))
            if isinstance(new_item['price'], tuple):
                self.log("[[TESTING]] Item price is tuple")
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

        logging.error("Brand matches: %s" % brand_matches)
        logging.error("Matches: %s" % name_matches)
        logging.error("SKU Matches: %s" % sku_matches)
        logging.error("Match score: %s" % score)
        logging.error("Match partial score: %s" % partial_score)
        logging.error("Match price: %s" % price_matches)
        logging.error("Match price soft: %s" % price_matches_soft)
        logging.error("Product matches: %s" % product_matches)
        logging.error("===================================================")

        contains_excluded_words = any([self.match_text(x, new_item) for x in minifigures_words])

        return brand_matches \
            and product_matches  \
            and not contains_excluded_words

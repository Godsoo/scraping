# -*- coding: utf-8 -*-
import os
import csv
import cStringIO
from decimal import Decimal

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from product_spiders.utils import extract_price
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

HERE = os.path.abspath(os.path.dirname(__file__))


class LegoNLAmazonCoUkSpider(BaseLegoAmazonSpider):
    name = 'lego-nl-amazon.co.uk-direct'
    lego_amazon_domain = 'www.amazon.co.uk'
    amazon_direct = True
    _use_amazon_identifier = True

    allowed_domains = ['xe.com', 'amazon.co.uk']
    exchange_rate = 0

    f_skus_found = os.path.join(HERE, 'amazon_direct_skus.txt')

    skus_found = []
    errors = []

    user_agent = 'spd'

    def get_search_query_generator(self):
        self._lego_prices = {}
        with open(os.path.join(HERE, 'legonl_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Item no'] and row['RRP price EUR']:
                    self._lego_prices[row['Product No.']] = round(extract_price(row['RRP price EUR']) * Decimal(0.83), 2)

        with open(os.path.join(HERE, 'lego_amazon_co_uk.csv')) as f:
            reader = csv.reader(cStringIO.StringIO(f.read()))
            for row in reader:
                # if row[0] not in ('75015', '79011', '79012', '79013', '79014'): continue
                item_search = {'sku': row[0],
                               'name': row[2],
                               'category': row[6]}
                if item_search['sku'] in self._lego_prices:
                    item_search['price'] = self._lego_prices[item_search['sku']]
                else:
                    item_search['price'] = None
                yield (
                    'LEGO ' + row[0],
                    item_search
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
            and not contains_excluded_words \
            and not self._excluded_product(new_item['name']) \
            and self._valid_terms(new_item['name'])

    def _valid_terms(self, item_name):
        result = super(LegoNLAmazonCoUkSpider, self)._valid_terms(item_name)
        if result:
            exclude_terms = ['Mega Bloks']
            for term in exclude_terms:
                if term in item_name:
                    return False
        return True

    def start_requests(self):
        yield Request('http://www.xe.com/currencyconverter/convert/?Amount=1&From=GBP&To=EUR', callback=self.start_amazon_requests)

    def start_amazon_requests(self, response):
        """
        The method serves as usual `start_requests`
        """
        hxs = HtmlXPathSelector(response)
        exchange_rate = hxs.select('//span[@class="uccResultAmount"]//text()').re('[\d\.]+')[0]

        self.exchange_rate = extract_price(exchange_rate)

        return super(LegoNLAmazonCoUkSpider, self).start_requests()

    def transform_price(self, price):
        try:
            price = extract_price(price)
        except:
            price = price
        return price * self.exchange_rate

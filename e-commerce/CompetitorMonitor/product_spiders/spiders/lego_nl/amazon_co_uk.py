import os
import csv
import cStringIO
from decimal import Decimal

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.exceptions import CloseSpider, DontCloseSpider

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

class LegoNLAmazonCoUkSpider(BaseLegoAmazonSpider):
    name = 'lego-nl-amazon.co.uk'
    all_sellers = True
    exclude_sellers = ['Amazon']

    allowed_domains = ['xe.com', 'amazon.co.uk']
    exchange_rate = 0

    f_skus_found = os.path.join(HERE, 'amazon_skus.txt')

    skus_found = []
    errors = []

    lego_amazon_domain = 'www.amazon.co.uk'

    def __init__(self, *args, **kwargs):
        super(LegoNLAmazonCoUkSpider, self).__init__(*args, **kwargs)
        self._lego_prices = {}

    def get_search_query_generator(self):
        with open(os.path.join(HERE, 'legonl_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Item no'] and row['RRP price EUR']:
                    self._lego_prices[row['Product No.']] = \
                        round(extract_price(row['RRP price EUR']) * Decimal(0.83), 2)

        with open(os.path.join(HERE, 'legonl_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                item_search = {'sku': row['Product No.'],
                               'name': row['Item Description English'],
                               'category': row['Theme']}
                if item_search['sku'] in self._lego_prices:
                    item_search['price'] = self._lego_prices[item_search['sku']]
                yield (
                    'LEGO ' + row['Product No.'],
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
            and not contains_excluded_words \
            and super(LegoNLAmazonCoUkSpider, self).match(meta, search_item, new_item)

    def _valid_terms(self, item_name):
        result = super(LegoNLAmazonCoUkSpider, self)._valid_terms(item_name)
        if result:
            exclude_terms = ['Mega Bloks', 'from set']
            for term in exclude_terms:
                if term in item_name:
                    return False
        return True

    def start_requests(self):
        yield Request('http://www.xe.com/currencyconverter/convert/?Amount=1&From=GBP&To=EUR', callback=self.start_amazon_requests)

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

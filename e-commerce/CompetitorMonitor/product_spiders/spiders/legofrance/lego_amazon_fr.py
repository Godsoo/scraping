import os
import re
import cStringIO

from product_spiders.utils import unicode_csv_dict_reader, extract_price_eu

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.base_spiders.amazonspider2 import BaseLegoAmazonSpider
from product_spiders.base_spiders.amazonspider2.legoamazonspider import (
    name_fuzzy_match,
    sku_match,
    name_fuzzy_score,
    name_fuzzy_partial_score,
    check_price_valid,
    filter_category,
    minifigures_words
)

class LegoAmazonSpider(BaseLegoAmazonSpider):
    name = 'lego-fr-amazon.com'
    all_sellers = True
    exclude_sellers = ['Amazon']

    f_skus_found = os.path.join(HERE, 'amazon_skus.txt')

    skus_found = []
    errors = []

    lego_amazon_domain = 'www.amazon.fr'

    def extract_price(self, price):
        """
        override extract price cause French site has different number format: #.###,##
        """
        return extract_price_eu(price)

    def get_search_query_generator(self):
        with open(os.path.join(HERE, 'lego.csv')) as f:
            reader = unicode_csv_dict_reader(cStringIO.StringIO(f.read()))
            for i, row in enumerate(reader):
                yield (
                    'LEGO ' + row['sku'],
                    {
                        'sku': row['sku'],
                        'name': row['name'],
                        'category': row['category'],
                        'price': row['price'],
                    }
                )

    def match(self, meta, search_item, new_item):
        import logging
        logging.error("===================================================")
        logging.error(search_item)
        logging.error(new_item)
        logging.error(self.match_lego_name(search_item, new_item))

        brand = new_item.get('brand').upper() if new_item.get('brand') else 'no brand'
        name = filter_category(new_item['name'], search_item['category'])
        logging.error("Filterer name: %s" % name)
        brand_matches = brand == 'LEGO' or brand.startswith('LEGO ') \
            or 'LEGO' in brand or brand in re.sub(r'[^\w]', ' ', search_item['category'].upper())\
            or 'LEGO' in new_item['name'].upper()
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

        contains_excluded_words = any([self.match_text(x, new_item) for x in minifigures_words])

        return brand_matches \
            and product_matches  \
            and not contains_excluded_words \
            and super(LegoAmazonSpider, self).match(meta, search_item, new_item)

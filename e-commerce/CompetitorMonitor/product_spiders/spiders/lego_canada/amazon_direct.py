import os
import csv
from scrapy.http import Request
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
    name = 'legocanada-amazon.ca-direct'

    # all_sellers = False
    _use_amazon_identifier = True
    # sellers = ['Amazon']
    amazon_direct = True

    f_skus_found = os.path.join(HERE, 'amazon_skus.txt')

    skus_found = []
    errors = []

    lego_amazon_domain = 'www.amazon.ca'
    seller_id_required = True
    cache_filename = os.path.join(HERE, 'amazon_data.csv')

    user_agent = 'spd'

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'amazondirect_map_deviation.csv')
    map_screenshot_method = 'scrapy_response'
    map_screenshot_html_files = {}

    def process_collected_products(self):
        for item in super(LegoAmazonSpider, self).process_collected_products():
            yield Request(item['url'], callback=self.save_product_page_html, meta={'product': item})

    def save_product_page_html(self, response):
        product = response.meta['product']
        html_path = os.path.join(HERE, '%s.html' % product['identifier'])
        with open(html_path, 'w') as f_html:
            f_html.write(response.body)
        self.map_screenshot_html_files[product['identifier']] = html_path

        yield product

    def get_search_query_generator(self):
        with open(os.path.join(HERE, 'legocanada_products.csv')) as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                # if row['sku'] not in ('4436',): continue
                yield (
                    'LEGO ' + row['Product Number'],
                    {
                        'sku': row['Product Number'],
                        'name': row['Product Description'],
                        'category': row['Theme'].decode('utf8'),
                        'price': extract_price(row['RRP']),
                    })

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
            and super(LegoAmazonSpider, self).match(meta, search_item, new_item)

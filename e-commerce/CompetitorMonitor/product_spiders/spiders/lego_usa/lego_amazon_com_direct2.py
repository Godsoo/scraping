import os

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.spiders.lego_usa.lego_amazon_base_spider import BaseLegoAmazonUSASpider

class LegoAmazonSpiderTest(BaseLegoAmazonUSASpider):
    name = 'lego-usa-amazon.com-direct[test]'
    _use_amazon_identifier = True
    amazon_direct = True
    collect_reviews = False
    review_date_format = u'%m/%d/%Y'

    user_agent = 'spd'

    skus_found = []
    errors = []

    lego_amazon_domain = 'www.amazon.com'

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'amazondirect_map_deviation.csv')

    def _collect_amazon_direct(self, product, meta):
        self._collect_best_match(product, meta['search_string'])

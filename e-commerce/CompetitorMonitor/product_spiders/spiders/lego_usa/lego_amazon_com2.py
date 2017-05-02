import os

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.spiders.lego_usa.lego_amazon_base_spider import BaseLegoAmazonUSASpider


class LegoAmazonSpiderTest(BaseLegoAmazonUSASpider):
    name = 'lego-usa-amazon.com[test]'
    all_sellers = True
    download_delay = 1.0
    exclude_sellers = ['Amazon']
    exclude_products = ['DEATH STAR II',
                        'LEGO Sydney Opera House',
                        'New offers for LEGO Sydney Opera House']

    collect_reviews = True
    review_date_format = u'%m/%d/%Y'

    user_agent = 'spd'

    f_skus_found = os.path.join(HERE, 'amazon_skus.txt')

    skus_found = []
    errors = []
    lego_amazon_domain = 'www.amazon.com'
    seller_id_required = True
    cache_filename = os.path.join(HERE, 'amazon_data.csv')

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'amazon_map_deviation.csv')

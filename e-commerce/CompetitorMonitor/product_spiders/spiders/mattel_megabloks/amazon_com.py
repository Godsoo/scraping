import os
import csv

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider
from product_spiders.base_spiders.amazonspider2.scraper import AmazonScraper

HERE = os.path.abspath(os.path.dirname(__file__))


class AmazonScraperCustom(AmazonScraper):

    def scrape_reviews_list_page(self, response, inc_selector=False, collect_author=False, collect_author_url=False):
        review_data = super(AmazonScraperCustom, self).scrape_reviews_list_page(
            response, inc_selector, collect_author=collect_author, collect_author_url=collect_author_url)
        if review_data['reviews']:
            for review in review_data['reviews']:
                full_text = review['full_text']
                text_splitted = full_text.split('\n')
                # <title> * <body>
                review['full_text'] = ' #&#&#&# '.join([text_splitted[0], '\n'.join(text_splitted[1:])])
                if 'verified purchase' in review['review_selector'].extract().lower() or \
                    review['review_selector'].select('//span[contains(text(), "(VINE VOICE)")]'):
                        review['full_text'] += ' #&#&#&# '
                if 'verified purchase' in review['review_selector'].extract().lower():
                    review['full_text'] += '\nVerified purchase'
                if review['review_selector'].select('//span[contains(text(), "(VINE VOICE)")]'):
                    review['full_text'] += '\nVine Voice'

        return review_data


class MattelAmazonDirectSpider(BaseAmazonSpider):
    """
    Check to see if BSM method is required for this spider, in this case construct_product will not work!
    Ask Yuri what to do in this case.
    """
    name = 'mattel-amazon.com-direct'
    domain = 'www.amazon.com'

    max_pages = 1
    do_retry = True
    collect_new_products = True
    collect_used_products = False
    amazon_direct = True
    try_match_product_details_if_product_list_not_matches = True
    collect_reviews = True
    reviews_inc_selector = True
    model_as_sku = True

    scraper_class = AmazonScraperCustom

    def __init__(self, *args, **kwargs):
        super(MattelAmazonDirectSpider, self).__init__(*args, **kwargs)
        self.try_suggested = False

    def get_search_query_generator(self):
        with open(os.path.join(HERE, 'mattelproducts.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                s_item = {
                    'name': row['NAME'],
                    'brand': row['BRAND'],
                }
                yield (row['NAME'], s_item)

    def match(self, meta, search_item, found_item):
        return True

    def construct_product(self, item, meta=None, use_seller_id_in_identifier=None):
        product = super(MattelAmazonDirectSpider, self).construct_product(item, meta=None, use_seller_id_in_identifier=None)
        product['brand'] = self.current_search_item['brand']
        return product

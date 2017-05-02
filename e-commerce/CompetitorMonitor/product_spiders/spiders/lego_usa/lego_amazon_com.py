import os

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.spiders.lego_usa.lego_amazon_base_spider import BaseLegoAmazonUSASpider
from product_spiders.base_spiders.amazonspider2.legoamazonspider import LegoAmazonScraper


class AmazonScraperCustom(LegoAmazonScraper):

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


class LegoAmazonSpider(BaseLegoAmazonUSASpider):
    name = 'lego-usa-amazon.com'

    all_sellers = True

    exclude_sellers = ['Amazon']
    exclude_products = ['DEATH STAR II',
                        'LEGO Sydney Opera House',
                        'New offers for LEGO Sydney Opera House']

    collect_reviews = True
    review_date_format = u'%m/%d/%Y'
    reviews_inc_selector = True

    retry_search_not_found = True

    f_skus_found = os.path.join(HERE, 'amazon_skus.txt')

    skus_found = []
    errors = []
    lego_amazon_domain = 'www.amazon.com'
    seller_id_required = True
    cache_filename = os.path.join(HERE, 'amazon_data.csv')

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'amazon_map_deviation.csv')

    scraper_class = AmazonScraperCustom

    retry_vendor_name = False

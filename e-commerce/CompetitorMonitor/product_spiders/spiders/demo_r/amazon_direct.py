import os
import csv
import paramiko
from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider
from product_spiders.base_spiders.amazonspider2.scraper import AmazonUrlCreator
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


class DemoRAmazonSpider(BaseAmazonSpider):
    name = 'demo_r-amazon.co.uk-direct'
    domain = "amazon.co.uk"

    type = 'asins'
    all_sellers = False
    amazon_direct = True

    file_path = HERE + '/demo_r_amazon.csv'

    def get_asins_generator(self):
        with open(self.file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['url'].strip():
                    yield (AmazonUrlCreator.get_product_asin_from_url(row['url']), '')

    def match(self, meta, search_item, found_item):
        return True

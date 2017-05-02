# -*- coding: utf-8 -*-
import csv
import os
import paramiko
from time import sleep

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider, AmazonScraper
from product_spiders.base_spiders.primary_spider import PrimarySpider

from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

from scrapy.http import Request
from scrapy.exceptions import CloseSpider
from brands import BrandSelector

HERE = os.path.abspath(os.path.dirname(__file__))


class AmazonToyMonitorScraper(AmazonScraper):
    def scrape_product_details_page(self, response, only_color=False, collect_new_products=True,
                                    collect_used_products=False):
        product = super(AmazonToyMonitorScraper, self).scrape_product_details_page(
                        response, only_color=False, collect_new_products=True,collect_used_products=False)

        product['brand'] = response.meta['category']
        return product


class AmazonSpiderDirect(BaseAmazonSpider, PrimarySpider):
    name = 'toymonitor-amazon.co.uk'
    domain = 'amazon.co.uk'

    type = 'category'
    model_as_sku = False
    use_amazon_identifier = True
    amazon_direct = False
    sellers = []
    exclude_sellers = []
    only_buybox = True
    all_sellers = False
    lowest_product_and_seller = False
    collect_products_with_no_dealer = True
    do_retry = True
    parse_options = False
    max_retry_count = 50
    retry_sleep = 5
    _max_pages = 400
    scraper_class = AmazonToyMonitorScraper
    #collect_products_from_list = True
    dealer_is_mandatory = False

    collect_reviews = True
    reviews_only_matched = True
    reviews_once_per_product_without_dealer = True

    try_suggested = False

    csv_file = 'toymonitor_amazon_crawl.csv'
    errors = []
    brand_selector = BrandSelector(errors)
    #field_modifiers = {'brand': brand_selector.get_brand}
    
    def _start_requests(self):
        self.products_count = 0

    def match(self, meta, search_item, found_item):
        return True

    def get_category_url_generator(self):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "tF9Z5DYK"
        username = "toymonitor"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        file_path = HERE + '/amazon.csv'
        sftp.get('amazon.csv', file_path)

        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield (row['URL'], row['Brand'])


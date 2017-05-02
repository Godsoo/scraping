# -*- coding: utf-8 -*-
__author__ = 'juraseg'
import csv
import os.path

import paramiko

from product_spiders.base_spiders.primary_spider import PrimarySpider

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider
from product_spiders.base_spiders.unified_marketplace_spider import UnifiedMarketplaceSpider
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT


HERE = os.path.abspath(os.path.dirname(__file__))


class AmazonCoUkDirectSpider(BaseAmazonSpider, UnifiedMarketplaceSpider):
    name = "demo_manufacturer-amazon.co.uk_direct"
    domain = "amazon.co.uk"
    market_type = 'direct'
    data_filename = 'demo_manufacturer_amazoncouk'

    type = ['asins', 'search']
    all_sellers = True
    parse_options = True
    collect_products_with_no_dealer = True

    try_suggested = False

    max_pages = 1
    model_as_sku = True

    reviews_only_matched = False
    collect_products_from_list = False
    collect_reviews = True
    reviews_collect_author = True
    reviews_collect_author_location = True

    scrape_categories_from_product_details = True

    data_filepath_local = HERE + '/usn_client_file.csv'

    def get_asins_generator(self):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "dy6ZqECj"
        username = "ultimatesportsnutrition"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        remote_filename = 'usn_client_file.csv'

        sftp.get(remote_filename, self.data_filepath_local)

        with open(self.data_filepath_local) as f:
            reader = csv.DictReader(f, delimiter=',')
            for i, row in enumerate(reader, 1):
                asin = row['ASIN']
                sku = row['Item Code']
                yield asin, sku

    def get_search_query_generator(self):
        competitor_rows = ['Sci-MX', 'Optimum Nutrition', 'BSN', 'PHD', 'Maxi Nutrition', 'Reflex', 'Mutant',
                           'Cellucor']
        competitor_mapping = {
            'Maxi Nutrition': 'MaxiNutrition',
        }
        with open(self.data_filepath_local) as f:
            reader = csv.DictReader(f, delimiter=',')
            for i, row in enumerate(reader, 1):
                product_name = row['Product Description']
                price = row['RRP']
                item = {
                    'name': product_name,
                    'price': price,
                }
                for c in competitor_rows:
                    if c in competitor_mapping:
                        brand = competitor_mapping[c]
                    else:
                        brand = c
                    search_query = row[c]
                    if search_query.lower().strip() != 'n/a':
                        search_query = brand + ' ' + search_query
                        yield search_query, item

    def match(self, meta, search_item, found_item):
        if 'TEENAGE MUTANT' in found_item['name'].upper().strip():
            return False

        return True

    def construct_product(self, item, meta=None, use_seller_id_in_identifier=None):
        r = super(AmazonCoUkDirectSpider, self).construct_product(item, meta, use_seller_id_in_identifier)
        if 'dealer' in r and r['dealer'] == 'Amazon':
            r['dealer'] = ''

        competitor_rows = ['Sci-MX', 'Optimum Nutrition', 'BSN', 'PHD', 'Maxi Nutrition', 'Reflex', 'Mutant',
                           'Cellucor']

        collected_brand = r.get('brand', '').lower()
        if 'pvl' in collected_brand:
            r['brand'] = 'Mutant'
        elif 'reflex nutrition' in collected_brand:
            r['brand'] = 'Reflex'
        elif 'phd nutrition' in collected_brand or 'phd' in collected_brand:
            r['brand'] = 'PhD'
        elif 'sci-mx nutrition' in collected_brand or 'sci mx' in collected_brand:
            r['brand'] = 'Sci-Mx'
        elif 'maximuscle' in collected_brand:
            r['brand'] = 'Maxi Nutrition'
        elif 'optimum' in collected_brand:
            r['brand'] = 'Optimum Nutrition'
        elif 'maxinutrition' in collected_brand:
            r['brand'] = 'Maxi Nutrition'
        elif 'unknown' in collected_brand:
            for brand in competitor_rows:
                if brand.replace(' ', '').lower() in r['name'].lower():
                    r['brand'] = brand

        if self.type == 'asins':
            metadata = r.get('metadata', None)
            if not metadata:
                r['metadata'] = {
                    'asin': item['asin'],
                }
            else:
                r['metadata']['asin'] = item['asin']

        return r

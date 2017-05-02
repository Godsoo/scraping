# -*- coding: utf-8 -*-
"""
This Amazon spider is set to search for items using the client's SFTP CSV data_filename
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/4210-navico-amer---new-site---amazon-us/details
"""
import csv
import os.path

import paramiko

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider
from product_spiders.base_spiders.unified_marketplace_spider import UnifiedMarketplaceSpider
from product_spiders.utils import remove_punctuation_and_spaces
from product_spiders.fuzzywuzzy.fuzz import ratio as fuzzy_match_ratio
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT


HERE = os.path.abspath(os.path.dirname(__file__))


class AmazonComSpider(BaseAmazonSpider, UnifiedMarketplaceSpider):
    name = "navico_amer_amazoncom"
    domain = "amazon.com"
    market_type = 'marketplace'
    data_filename = 'navico_amazoncom'

    type = ['search']
    all_sellers = True
    parse_options = True
    collect_products_with_no_dealer = True

    try_suggested = False

    model_as_sku = False

    scrape_categories_from_product_details = True

    def get_search_query_generator(self):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "A7Ct8rLX07n"
        username = "navico"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        remote_filename = 'navico_feed_amer.csv'
        data_filepath_local = os.path.join(HERE, 'navico_feed_amazon.csv')

        sftp.get(remote_filename, data_filepath_local)

        items = []
        with open(data_filepath_local) as f:
            reader = csv.DictReader(f, delimiter=',')
            for i, row in enumerate(reader, 1):
                item = {
                    'name': row['Product.Name'],
                    'sku': row['Product.BaseSKU'],
                    'brand': row.get('Brand.CUST', '')
                }
                items.append(item)

        remote_filename = 'navico_screensize_products.csv'
        data_filepath_local = os.path.join(HERE, 'navico_screensize_products_amazon.csv')

        sftp.get(remote_filename, data_filepath_local)

        with open(data_filepath_local) as f:
            reader = csv.DictReader(f, delimiter=',')
            for i, row in enumerate(reader, 1):
                item = {
                    'name': row['Description'],
                    'sku': row['Manufacturer Part Number'],
                    'brand': row['Brand']
                }
                items.append(item)

        self.brands = set([x['brand'].lower() for x in items])
        self.log("[[NAVICO_AMER_AMAZON]] Collected brands: {}".format(", ".join(self.brands)))

        for i, item in enumerate(items, 1):
            search_query = item['sku']
            yield search_query, item

    def match(self, meta, search_item, found_item):
        if 'rachael ray' in (found_item.get('brand', '') or '').lower():
            self.log(u'[[NAVICO_AMER_AMAZON]] found Rachael Ray item: {brand} {name} ({url})'.format(**found_item))
            return False
        if 'e-cloth' in found_item['name'].lower():
            self.log(u'[[NAVICO_AMER_AMAZON]] found e-cloth item: {brand} {name} ({url})'.format(**found_item))
            return False
        if not found_item.get('brand'):
            self.log(u"[[NAVICO_AMER_AMAZON]] found item with no brand: {name} ({url})".format(**found_item))
        elif (found_item.get('brand', '') or '').lower() not in self.brands:
            self.log(u"[[NAVICO_AMER_AMAZON]] found item with incorrect brand: {brand} {name} ({url})".format(**found_item))
        if 'model' in found_item:
            self.log(u"[[NAVICO_AMER_AMAZON]] Found model for product {}: {}".format(found_item['name'], found_item['model']))
            search_sku = remove_punctuation_and_spaces(search_item['sku']).lower()
            found_sku = remove_punctuation_and_spaces(found_item['model']).lower()
            if fuzzy_match_ratio(search_sku, found_sku) >= 90:
                self.log("[[NAVICO_AMER_AMAZON]] Model {} match sku {}".format(found_item['model'], search_item['sku']))
                return True
            self.log(u"[[NAVICO_AMER_AMAZON]] Model {} do not match sku {}".format(found_item['model'], search_item['sku']))
            return False
        else:
            self.log(u"[[NAVICO_AMER_AMAZON]] No model for product {}: {}".format(found_item['name'], found_item['url']))
            return True

    def construct_product(self, item, meta=None, use_seller_id_in_identifier=None):
        r = super(AmazonComSpider, self).construct_product(item, meta, use_seller_id_in_identifier)
        r['brand'] = meta['search_item']['brand']
        r['sku'] = meta['search_item']['sku']

        return r

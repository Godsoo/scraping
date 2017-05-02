# -*- coding: utf-8 -*-
"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4882

The spider uses amazon base spider, asins type.

"""
import os
import csv
import paramiko

from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider

HERE = os.path.abspath(os.path.dirname(__file__))



class BaseAndrewJamesAmazonCoUkSpider(BaseAmazonSpider):
    domain = 'amazon.co.uk'

    name = 'andrewjames-amazon.co.uk'

    type = 'asins'
    all_sellers = True
    exclude_sellers = ['Amazon']
    fulfilled_by_amazon_to_identifier = True

    _use_amazon_identifier = True

    parse_options = True

    collect_reviews = True
    reviews_only_verified = True
    reviews_only_matched = False

    do_retry = True
    max_pages = None

    brands = []

    file_path = HERE + '/andrewjames_amazon_asins.csv'

    def get_asins_generator(self):


        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "5H3xcABq"
        username = "andrewjames"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        sftp.get('Competitor Monitor.csv', self.file_path)

        with open(self.file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['ASIN'].strip():
                    yield (row['ASIN'], row['SKU'])

    def match(self, meta, search_item, found_item):
        return True

    def construct_product(self, item, meta=None, use_seller_id_in_identifier=None):
        r = super(BaseAndrewJamesAmazonCoUkSpider, self).construct_product(item, meta, use_seller_id_in_identifier)

        if self.type == 'asins':
            metadata = r.get('metadata', None)
            if not metadata:
                r['metadata'] = {
                    'asin': item['asin'],
                }
            else:
                r['metadata']['asin'] = item['asin']

        return r

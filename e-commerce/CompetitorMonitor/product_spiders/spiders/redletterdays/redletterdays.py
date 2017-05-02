# -*- coding: utf-8 -*-
import os
import csv
import paramiko
from decimal import Decimal

from redletterdaysitem import RedLetterDaysMeta

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


class RedLetterDaysSpider(SecondaryBaseSpider):
    name = "redletterdays-redletterdays.co.uk"
    allowed_domains = ('redletterdays.co.uk', )
    start_urls = ['http://www.redletterdays.co.uk']

    csv_file = 'buyagift/redletterdays.co.uk_products.csv'

    feed_file = os.path.join(HERE, 'redletterdays.csv')

    feed_products = {}

    def start_requests(self):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        username = "redletterdays"
        password = "hE23id1Z"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.get('redletterdays.csv', self.feed_file)

        with open(self.feed_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.feed_products[row['Exp Ref'].upper().strip()] = row

        for req in list(super(RedLetterDaysSpider, self).start_requests()):
            yield req

    def preprocess_product(self, item):
        feed_product = self.feed_products.get(item['sku'].upper())
        if not feed_product:
            return
        item['category'] = feed_product['Category']
        metadata = RedLetterDaysMeta()
        cost_price = Decimal(feed_product['Cost'].decode('latin_1').strip(u'\xa3'))
        metadata['cost_price'] = "{:0.2f}".format(cost_price)
        item['metadata'] = metadata
        return item

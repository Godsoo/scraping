"""
Name: navico-amer-googleshopping
Original developer: Emiliano M. Rudenick <emr.frei@gmail.com>
Ticket reference: https://www.assembla.com/spaces/competitormonitor/tickets/4212

IMPORTANT:

- Local proxies management. It uses Proxy Service.
- Use of PhantomJS to browse the website.
- PLEASE be CAREFUL, Google bans the proxies quickly.
"""

import os
import csv

import paramiko

from product_spiders.base_spiders import GoogleShoppingBaseSpider
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


class NavicoGoogleShoppingSpider(GoogleShoppingBaseSpider):
    name = 'navico-amer-googleshopping'
    allowed_domains = ['google.com']
    start_urls = ['https://www.google.com/shopping?hl=en']

    SHOPPING_URL = 'https://www.google.com/shopping?hl=en'
    ACTIVE_BROWSERS = 10

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1',
        'Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; rv:33.0) Gecko/20100101 Firefox/33.0',
        'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:24.0) Gecko/20100101 Firefox/24.0',
        'Mozilla/5.0 (X11; Linux i586; rv:31.0) Gecko/20100101 Firefox/31.0',
        'Mozilla/5.0 (X11; Linux x86_64; rv:24.0) Gecko/20100101 Firefox/24.0',
        'Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:24.0) Gecko/20100101 Firefox/24.0',
    ]

    parse_all = True
    parse_reviews = False

    def search_iterator(self):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "A7Ct8rLX07n"
        username = "navico"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        csv_file = os.path.join(HERE, 'navico_feed_google.csv')

        sftp.get('navico_feed_amer.csv', csv_file)

        with open(csv_file) as f:
            reader = csv.DictReader(f, delimiter=',')
            for i, row in enumerate(reader, 1):
                item = {
                    'sku': row['Product.BaseSKU'],
                    'brand': row.get('Brand.CUST', '')
                }

                search = item['sku']
                yield (search, item, ['sku', 'brand'])

        remote_filename = 'navico_screensize_products.csv'
        csv_file = os.path.join(HERE, 'navico_screensize_products_google.csv')

        sftp.get(remote_filename, csv_file)

        with open(csv_file) as f:
            reader = csv.DictReader(f, delimiter=',')
            for i, row in enumerate(reader, 1):
                item = {
                    'sku': row['Manufacturer Part Number'],
                    'brand': row['Brand']
                }

                search = item['sku']
                yield (search, item, ['sku', 'brand'])

    def match_item(self, item):
        if 'chelsea' in item['name'].lower():
            self.log("[NAVICO_AMER_GOOGLE] found item with 'chelsea': {brand} {name} ({url})".format(**item))
            return False
        return super(NavicoGoogleShoppingSpider, self).match_item(item)

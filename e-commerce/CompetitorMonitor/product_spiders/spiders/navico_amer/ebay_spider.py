import os
import re
import csv
import shutil
import paramiko
import cStringIO

from decimal import Decimal

from scrapy.selector import HtmlXPathSelector

from product_spiders.base_spiders import BaseeBaySpider
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


class NavicoAMEREbaySpider(BaseeBaySpider):

    HERE = os.path.abspath(os.path.dirname(__file__))

    name = 'navico-amer-ebay.com'

    def __init__(self, *args, **kwargs):
        super(NavicoAMEREbaySpider, self).__init__()
        self._csv_file = os.path.join(self.HERE, 'navico_feed.csv')
        self._converted_price = True
        self._ebay_url = 'http://www.ebay.com'
        self._search_fields = ['sku']
        self._tp32_search_fields = ['brand', 'sku']
        self._all_vendors = True
        self._look_related = False
        self._meta_fields = [('sku', 1),
                             ('brand', 0),]

        self._check_valid_item = self._valid_item_

        self._check_diff_ratio = False

    def start_requests(self):

        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "A7Ct8rLX07n"
        username = "navico"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        csv_file = os.path.join(HERE, 'navico_feed_ebay.csv')

        sftp.get('navico_feed_amer.csv', csv_file)

        number = 0
        with open(csv_file) as f:
            reader = csv.DictReader(f, delimiter=',')
            for row in reader:
                number += 1
                meta = {
                    'sku': row['Product.BaseSKU'],
                    'brand': row.get('Brand.CUST', '')
                }
                if meta['sku'].lower() == 'tp32':
                    search = ' '.join(meta[field].strip() for field in self._tp32_search_fields)
                else:
                    search = ' '.join(meta[field].strip() for field in self._search_fields)
                meta.update({'search': search})
                # Get URL
                search = self._clean_search(search)  # Clean search
                url = self._get_url_search('"' + search + '"')
                self.log('Item %s | Search by: %s' % (number, search))
                yield self._search(url, meta)

        remote_filename = 'navico_screensize_products.csv'
        csv_file = os.path.join(HERE, 'navico_screensize_products_ebay.csv')

        sftp.get(remote_filename, csv_file)

        with open(csv_file) as f:
            reader = csv.DictReader(f, delimiter=',')
            for i, row in enumerate(reader, 1):
                number += 1
                meta = {
                    'sku': row['Manufacturer Part Number'],
                    'brand': row['Brand']
                }
                if meta['sku'].lower() == 'tp32':
                    search = ' '.join(meta[field].strip() for field in self._tp32_search_fields)
                else:
                    search = ' '.join(meta[field].strip() for field in self._search_fields)
                meta.update({'search': search})
                # Get URL
                search = self._clean_search(search)  # Clean search
                url = self._get_url_search('"' + search + '"')
                self.log('Item %s | Search by: %s' % (number, search))
                yield self._search(url, meta)

    def load_item(self, *args, **kwargs):
        product_loader = super(NavicoAMEREbaySpider, self).load_item(*args, **kwargs)

        response = args[-1]

        hxs = HtmlXPathSelector(response=response)
        categories = hxs.select('//ul[contains(@itemtype,"Breadcrumblist")]//span/text()').extract()
        product_loader.replace_value('category', categories)
        return product_loader

    def _valid_item_(self, item_loader, response):
        return True


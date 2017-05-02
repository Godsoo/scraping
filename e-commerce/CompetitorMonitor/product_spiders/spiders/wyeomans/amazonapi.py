# coding=utf-8
__author__ = 'juraseg'

import os.path
import paramiko
import csv
import datetime

from scrapy.http.request import Request
from scrapy.exceptions import CloseSpider

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider, AmazonUrlCreator
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))

class YeomansAmazonAPISpider(BaseAmazonSpider):
    name = 'yeomans_amazonapi'
    allowed_domains = ['amazon.co.uk']
    exclude_sellers = ['Yeomans Outdoor Leisure']
    lowest_product_and_seller = True

    domain = 'amazon.co.uk'

    def __init__(self, *args, **kwargs):
        super(YeomansAmazonAPISpider, self).__init__(*args, **kwargs)

        self.errors = []

        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "giT4sWn5"
        username = "yeomans"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        remote_file = get_latest_asin_list_file(files)
        if not remote_file:
            self.errors.append("No file found on SFTP")
            raise CloseSpider("No file found on SFTP")

        file_path = HERE + '/asins.txt'
        sftp.get(remote_file, file_path)

        self.log("Loaded file: %s" % remote_file)

        with open(file_path) as f:
            reader = csv.DictReader(f, delimiter='\t')

            self.rows = list(reader)
            self.log("ASINs found: %d" % len(self.rows))

        self.errors.append("Spider works incorrectly: it should collect 'lowest seller', but that's not implemented")

    def get_search_query_generator(self):
        for i, row in enumerate(self.rows):
            yield ('', {'asin': row['asin'], 'sku': row['seller-sku']})

    def get_next_search_request(self, callback=None):
        """
        Creates search request using self.search_generator
        """
        if not self.search_generator:
            return []
        try:
            search_string, search_item = next(self.search_generator)
        except StopIteration:
            return []

        self.log('Checking product [%s]' % search_item['asin'])

        self.current_search = search_string
        self.current_search_item = search_item
        self.collected_items = []
        self.processed_items = False

        requests = []
        url = AmazonUrlCreator.build_url_from_asin(self.domain, search_item['asin'])

        if callback is None:
            callback = self.parse_product

        requests.append(Request(url, meta={'search_string': search_string, 'search_item': search_item},
                        dont_filter=True, callback=callback))

        return requests

    def match(self, meta, search_item, found_item):
        return True


def get_file_date(filename):
    try:
        res = datetime.datetime.strptime(filename, 'asin-numbers-%d%m%y.txt')
        res = res.date()
    except ValueError:
        res = None
    return res


def get_latest_asin_list_file(files):
    asin_files = []
    for file_rec in files:
        filename = file_rec.filename
        if not filename.startswith('asin-numbers-'):
            continue
        if not filename.endswith('.txt'):
            continue
        asin_files.append(filename)

    if not asin_files:
        return None

    latest_file = None
    latest_date = None

    for filename in asin_files:
        file_date = get_file_date(filename)
        if file_date:
            if not latest_date or latest_date < file_date:
                latest_file = filename
                latest_date = file_date
    if latest_file:
        return latest_file
    else:
        return None
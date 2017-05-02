from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider
from product_spiders.base_spiders.amazonspider2.scraper import AmazonScraper
from product_spiders.base_spiders.unified_marketplace_spider import UnifiedMarketplaceSpider
from product_spiders.base_spiders.primary_spider import PrimarySpider
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT
import csv
import paramiko
import os

HERE = os.path.abspath(os.path.dirname(__file__))

class LakeLandAmazonScraper(AmazonScraper):
    def scrape_product_details_page(self, response, only_color=False, collect_new_products=True,
                                    collect_used_products=False):
        product = super(LakeLandAmazonScraper, self).scrape_product_details_page(response, only_color, collect_new_products, collect_used_products)
        if response.xpath('//div[@id="addon"]'):
            product['addon'] = True
        return product

class LakeLandAmazonDirect(BaseAmazonSpider, UnifiedMarketplaceSpider, PrimarySpider):
    name = 'lakeland-amazon.co.uk-direct'
    type = ['asins', 'search']
    all_sellers = True
    domain = "amazon.co.uk"
    scrape_categories_from_product_details = True
    exclude_sellers = ['Lakeland']
    scraper_class = LakeLandAmazonScraper

    market_type = 'direct'
    data_filename = 'lakeland_amazon'

    file_path = HERE + '/lakeland.csv'

    csv_file = 'lakeland_amazon_direct_as_prim.csv'

    def __init__(self, *args, **kwargs):
        super(LakeLandAmazonDirect, self).__init__(*args, **kwargs)
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "Grq2SrjR"
        username = "lakeland"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        remote_file = "Lakeland.csv"

        sftp.get(remote_file, self.file_path)

        self.log("Loaded file: %s" % remote_file)

    def get_asins_generator(self):
        with open(self.file_path) as f:
            reader = csv.DictReader(f, delimiter="|")
            for row in reader:
                if row['ASIN']:
                    yield(row['ASIN'], row['Unique Product Code'])

    def get_search_query_generator(self):
        with open(self.file_path) as f:
            reader = csv.DictReader(f, delimiter="|")
            for row in reader:
                if row['ASIN']:
                    yield(row['ASIN'],
                          {'name': row['Product Name'], 'price': row['Price']})

    def match(self, meta, search_item, found_item):
        return True

    def construct_product(self, item, meta=None, use_seller_id_in_identifier=None):
        product = super(LakeLandAmazonDirect, self).construct_product(item, meta, use_seller_id_in_identifier)
        if 'dealer' in product and product['dealer'] == 'Amazon':
            product['dealer'] = ''
        if 'addon' in item:
            metadata = {'addon_item': "Yes"}
            product['metadata'] = metadata
        return product

    def retry_download(self, url, metadata, callback, blocked=False, headers=None):
        request = super(LakeLandAmazonDirect, self).retry_download(url, metadata, callback, blocked, headers)
        request = request.replace(errback=None)
        request.meta['recache'] = True
        return request

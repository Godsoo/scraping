import os
import csv
import paramiko
from scrapy.spider import BaseSpider

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))
from product_spiders.config import DATA_DIR
from brands import BrandSelector

class ToyMonitorDatabase(BaseSpider):
    name = 'toymonitor-database'

    start_urls = ('http://148.251.79.44/productspiders',)

    file_name = 'toymonitor_database.csv'
    errors = []
    brand_selector = None
    

    def __init__(self, *args, **kwargs):
        super(ToyMonitorDatabase, self).__init__(*args, **kwargs)
        self.seen_ids = set()

    def _get_prev_crawl_filename(self):
        filename = None
        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
        return filename

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        username = 'toymonitor'
        password = 'tF9Z5DYK'
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp_file = os.path.join(HERE, 'toymonitor_database.csv')
        sftp.get(self.file_name, sftp_file)
        sftp.get('brands.csv', os.path.join(HERE, 'brands.csv'))
        self.brand_selector = BrandSelector(self.errors)
        self.field_modifiers = {'brand': lambda x: self.brand_selector.get_brand(x)}
        previous_file = None  # self._get_prev_crawl_filename()

        csv_files = [sftp_file]
        if previous_file:
            csv_files.append(previous_file)

        for csv_file in csv_files:
            with open(csv_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['identifier'] in self.seen_ids:
                        continue
                    self.seen_ids.add(row['identifier'])
                    loader = ProductLoader(response=response, item=Product())
                    loader.add_value('identifier', row['identifier'])
                    loader.add_value('sku', row['sku'])
                    loader.add_value('name', row['name'].decode('utf-8'))
                    loader.add_value('brand', row['brand'].decode('utf-8'))
                    loader.add_value('category', row['category'].decode('utf-8'))
                    loader.add_value('price', row['price'])
                    loader.add_value('stock', None)
                    loader.add_value('shipping_cost', row['shipping_cost'])
                    loader.add_value('dealer', row['dealer'].decode('utf-8'))
                    loader.add_value('url', row['url'])
                    loader.add_value('image_url', row['image_url'])
                    yield loader.load_item()

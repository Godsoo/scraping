import os
import csv
import shutil
import paramiko

from cStringIO import StringIO

from scrapy.spider import BaseSpider
from scrapy.utils.url import url_query_parameter

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from product_spiders.spiders.thebookpeople.bookpeopleitem import BookpeopleMeta
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

HERE = os.path.abspath(os.path.dirname(__file__))


class TheBookPeopleSpider(BaseSpider):
    name = 'thebookpeople-longtail-thebookpeople.co.uk'

    start_urls = ('http://www.thebookpeople.co.uk',)

    def __init__(self, *args, **kwargs):
        super(TheBookPeopleSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def spider_closed(self, spider):
        shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(HERE, 'thebookpeople.co.uk_products.csv'))


    def parse(self, response):

        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "GsDCM9P2"
        username = "bookpeople"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        file_path = HERE + '/cm_extended.txt'

        sftp.get('cm_extended.txt', file_path)

        with open(file_path) as f:
            reader = csv.DictReader(StringIO(f.read().replace('"', '')), delimiter='|')
            for row in reader:
                loader = ProductLoader(response=response, item=Product())
                identifier = url_query_parameter(row['LINK'], 'productId')
                loader.add_value('identifier', identifier)
                loader.add_value('sku', row['GTIN'])
                loader.add_value('brand', row['BRAND'])
                categories = [cat for cat in row['COMMERCE_CATEGORY'].split('\\') if cat]
                loader.add_value('category', categories[:3])
                loader.add_value('url', row['LINK'])
                loader.add_value('name', row['TITLE'])
                loader.add_value('image_url', row['IMAGE_LINK'])
                out_of_stock = 'IN STOCK' not in row['AVAILABILITY'].upper()
                if out_of_stock:
                    loader.add_value('stock', 0)
                loader.add_value('price', row['PRICE'])
                item = loader.load_item()

                metadata = BookpeopleMeta()
                metadata['tbp_code'] = row['ID']
                metadata['uk_rrp'] = row['UK_RRP']
                metadata['feature'] = row['FEATURE']
                metadata['pages'] = row['PAGES']
                metadata['author'] = row['AUTHOR']
                metadata['quantity'] = row['QUANTITY']
                metadata['cost_price'] = row['COST_PRICE']
                item['metadata'] = metadata
                
                yield item


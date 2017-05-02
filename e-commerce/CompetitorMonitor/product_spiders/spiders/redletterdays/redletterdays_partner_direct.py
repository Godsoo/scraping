import os
import csv
import paramiko
from scrapy.http import Request
from scrapy.spider import BaseSpider


from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


class RLDPartnerDIrectSpider(BaseSpider):
    name = 'redletterdays-supplier'

    feed_file = os.path.join(HERE, 'redletterdays.csv')
    start_urls = ('file://' + feed_file,)

    def start_requests(self):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        username = "redletterdays"
        password = "hE23id1Z"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.get('redletterdays.csv', self.feed_file)

        yield Request(self.start_urls[0])

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['Exp Ref'].lower())
            loader.add_value('sku', row['Exp Ref'])
            loader.add_value('category', row['Category'])
            loader.add_value('name', row['Website Description'].decode('utf8', errors="ignore"))
            loader.add_value('price', row['Supplier'])
            yield loader.load_item()

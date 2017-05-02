"""
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5139
"""

import os
import csv
import paramiko

from scrapy.spiders import Spider
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price

from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

from bearmachitems import BearmachMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class BearMach(Spider):
    name = 'bearmach-bearmach'
    allowed_domains = ['http://bearmach.com/']
    start_urls = ['http://bearmach.com/']
    
    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "8PskJYFa"
        username = "bearmach"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        file_path = os.path.join(HERE, 'bearmach_products.csv')
        sftp.get('bearmach_feed.csv', file_path)

        with open(file_path) as f:
            reader = csv.DictReader(f)
            reader.fieldnames = [field.strip() for field in reader.fieldnames]
            for row in reader:
                loader = ProductLoader(Product(), response=None)
                loader.add_value('identifier', row['Bearmach Part Number'].decode('latin-1'))
                loader.add_value('sku', row['Bearmach Part Number'].decode('latin-1'))
                loader.add_value('name', row['Description'].decode('latin-1'))
                loader.add_value('brand', row['Brand'].decode('latin-1'))
                loader.add_value('price', row['Retail'].decode('latin-1'))
                loader.add_value('category', row['Product Group'])
                item = loader.load_item()

                metadata = BearmachMeta()
                metadata['cost_price'] = str(extract_price(row['Cost'].decode('latin-1')))
                metadata['supplier_code'] = row['Supplier Code'].strip()
                metadata['supplier_name'] = row['Supplier Name'].strip()

                item['metadata'] = metadata
                yield item

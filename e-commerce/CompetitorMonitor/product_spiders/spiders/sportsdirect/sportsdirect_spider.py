import re
import os
import csv
import paramiko

import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.item import Item, Field

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))

from sportsdirectitems import SportsDirectMeta


class SportsDirectSpider(BaseSpider):
    name = 'sportsdirect.com'
    allowed_domains = ['sportsdirect.com']

    start_urls = ['http://www.sportsdirect.com']

    def parse(self, response):
        base_url = get_base_url(response)

        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "Th482zQi"
        username = "sportsdirect"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()
        
        file_path = HERE + '/Products.csv'
        sftp.get(get_last_file(files).filename, file_path)

        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # ignore kids' shoes
                if 'c' in row[' Size'].lower():
                    continue
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('identifier', row['ProductCode'].lower())
                loader.add_value('sku', row['ProductCode'])
                loader.add_value('brand', row[' Brand'])
                loader.add_value('category', '')
                name = row[' ProductName'].decode('ISO-8859-1') + ' ' + row[' Colour'].decode('ISO-8859-1') + ' ' + row[' Size'].decode('ISO-8859-1')
                loader.add_value('name', name)
                loader.add_value('price', row[' Price'])
                loader.add_value('url', row[' ProductUri'])
                loader.add_value('image_url', row[' ImageUrl'])
                loader.add_value('shipping_cost', row[' ShippingCost'])
                try:
                    stock = int(row[' InStock'])
                except ValueError:
                    self.log('There is a problem for line with product identifier %s. The data can be wrong!' %row['ProductCode'])
                    stock = 0
                if not stock:
                    loader.add_value('stock', 0)
                meta = SportsDirectMeta()
                meta['rrp'] = row.get(' TicketPrice', '')
                meta['product_code'] = row[' SupplierProductCode']
                meta['size'] = row[' Size'].split('(')[0].strip().decode('ISO-8859-1')
                product = loader.load_item()
                product['metadata'] = meta
                yield product

def get_last_file(files):
    exts = ('.csv')
    last = None
    for f in files:
        if ((last == None and f.filename[-4:] in exts) or 
            (f.filename[-4:] in exts and 
             f.st_mtime > last.st_mtime)):
            last = f
    return last
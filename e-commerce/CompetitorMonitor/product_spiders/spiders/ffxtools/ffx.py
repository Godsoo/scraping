# -*- coding: utf-8 -*-
"""
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/3913-ffx-tools---new-site---ffx#/activity/ticket:
This spider searches for SKUs and extract the items.
IMPORTANT! The website returns an error response when too many SKUs are searched (it can be noticed using the browser too),
the mobile version does not seem to have this problem.
Some searches return errors, so the they are retried.
"""
import os
import re
import csv
import paramiko
import demjson
from StringIO import StringIO

from scrapy import log

from scrapy.item import Item, Field
from product_spiders.base_spiders.primary_spider import PrimarySpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from utils import extract_price


from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))

class FFXMeta(Item):
    barcode = Field()

class FFXToolsSpider(PrimarySpider):
    name = 'ffxtools-ffx.co.uk'
    allowed_domains = ['ffx.co.uk']
    start_urls = ['http://148.251.79.44/productspiders']
    # download_delay = 2

    csv_file = 'ffx.co.uk_products.csv'


    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "rShMnFEm"
        username = "ffxtools"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        last = get_last_file('ffxprices.csv', files)

        file_path = os.path.join(HERE, 'ffxprices.csv')
        sftp.get(last.filename, file_path)

        with open(file_path) as f:
            data = data = f.read().replace('\xef\xbb\xbf', '')
            reader = csv.DictReader(StringIO(data), delimiter=',')
            for row in reader:
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('name', row.get('Name').decode('utf-8', errors='ignore'))
                loader.add_value('url', row.get('Product_URL').decode('utf-8', errors='ignore'))
                loader.add_value('price', row.get('Price').decode('utf-8', errors='ignore'))
                loader.add_value('brand', row.get('Brand').decode('utf-8', errors='ignore'))
                loader.add_value('category', row.get('Category').decode('utf-8', errors='ignore'))
                loader.add_value('sku', row.get('SKU').decode('utf-8', errors='ignore'))
                loader.add_value('identifier', row.get('SKU').decode('utf-8', errors='ignore'))
                loader.add_value('image_url', row.get('Image_URL').decode('utf-8', errors='ignore'))
                loader.add_value('shipping_cost', row.get('Shipping_Costs').decode('utf-8', errors='ignore'))
                loader.add_value('stock', row.get('Availability').decode('utf-8', errors='ignore'))
                product = loader.load_item()
                metadata = FFXMeta()
                metadata['barcode'] = row.get('Barcode').decode('utf-8', errors='ignore')
                product['metadata'] = metadata
                yield product
                
def get_last_file(start_with, files):
    """
    Returns the most recent file, for the file name which starts with start_with

    :param start_with: the file name has this form start_with + date
    :param files: files list sftp.listdir_attr
    """
    last = None
    for f in files:
        if ((last == None and start_with in f.filename and 
             f.filename.endswith('.csv')) or 
            (start_with in f.filename and f.filename.endswith('.csv') and 
             f.st_mtime > last.st_mtime)):
            last = f
    return last

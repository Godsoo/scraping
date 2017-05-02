# -*- coding: utf-8 -*-

import re
import os
import csv
import shutil
import paramiko
from decimal import Decimal


from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse

from product_spiders.base_spiders import PrimarySpider
from product_spiders.utils import extract_price
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)

from scrapy.http import Request, HtmlResponse

from lakelanditems import LakelandMeta


HERE = os.path.abspath(os.path.dirname(__file__))


class LakelandSpider(PrimarySpider):
    name = 'lakeland-lakeland.co.uk'
    allowed_domains = ['lakeland.co.uk']
    filename = os.path.join(HERE, 'lakeland.csv')
    start_urls = ('http://www.lakeland.co.uk',)

    csv_file = 'lakeland_lakeland_as_prim.csv'


    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "Grq2SrjR"
        username = "lakeland"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        file_path = HERE+'/Lakeland_products.csv'
        sftp.get('Lakeland.csv', file_path)

        with open(file_path) as f:
            reader = csv.DictReader((line.replace('\x00', '') for line in f), delimiter="|")
            for row in reader:
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('sku', row['Unique Product Code'])
                loader.add_value('identifier', row['Unique Product Code'])
                loader.add_value('name', row['Product Name'])
                loader.add_value('category', row['Category'])
                loader.add_value('image_url', row['Image URL'])

                loader.add_value('brand', row['Brand'].decode('latin-1'))
                loader.add_value('url', row['Product Page URL'])
                list_price = str(round(extract_price(row['List Price']), 2))
                cost_price = str(round(extract_price(row['Cost Price']), 2))
                rrp = str(round(extract_price(row['RRP']), 2))
                selling_price = round(extract_price(row['Price']), 2)
                if selling_price > 0:
                    margin = ((Decimal(rrp) / Decimal('1.2') - Decimal(cost_price)) / Decimal(selling_price)) * Decimal('1.2')
                else:
                    margin = Decimal('0.00')
                margin *= Decimal('100')
                margin = '{}%'.format(str(round(extract_price(str(margin)), 2)))
                loader.add_value('price', selling_price)
                loader.add_value('stock', row['Stock Availability'])
                loader.add_value('shipping_cost', row['Shipping Cost'])
                item = loader.load_item()
                metadata = LakelandMeta()
                metadata['margin'] = margin
                metadata['promotional_message'] = row['Promotional Message']
                metadata['buyer_name'] = row['Buyer Name']
                metadata['list_price'] = list_price
                metadata['cost_price'] = cost_price
                metadata['asin'] = row['ASIN']
                metadata['dd'] = 'Yes' if row['DD'] == '1' else ''
                metadata['rrp'] = rrp
                item['metadata'] = metadata
                yield item

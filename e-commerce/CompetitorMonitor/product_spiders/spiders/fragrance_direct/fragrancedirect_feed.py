import os
import csv
import shutil
import paramiko

from scrapy.spider import BaseSpider
from scrapy.http import Request

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

from cStringIO import StringIO

from fragrancedirectitem import FragranceDirectMeta
from decimal import Decimal

HERE = os.path.abspath(os.path.dirname(__file__))


class FragranceDirectSpider(BaseSpider):
    name = 'fragrancedirect-feed'

    skus = []

    def start_requests(self):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "wHDeBfpj"
        username = "fragrancedirect"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        file_path = HERE+'/products_to_monitor.csv'
        sftp.get('PriceComparisonList.csv', file_path)

        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    sku = int(row['Code'].upper())
                except:
                    sku = row['Code'].upper()

                self.skus.append(sku)

        file_path = HERE+'/fragrancedirect_products.csv'
        sftp.get('Fragrance_Direct_Intelligent_Eye.csv', file_path)


        yield Request('file://' + file_path)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body), delimiter='|')
        for row in reader:
            loader = ProductLoader(response=response, item=Product())

            sku = row['\xef\xbb\xbfUnique product code']
            try:
                sku = int(sku)
            except:
                sku = sku

            if sku in self.skus:
                sku = row['\xef\xbb\xbfUnique product code']
                loader.add_value('identifier', sku.lower())
                loader.add_value('sku', sku)
                loader.add_value('brand', unicode(row['Brand'], 'iso-8859-1', errors='replace'))
                loader.add_value('category', row['Category'].decode('utf8'))
                loader.add_value('name', unicode(row['Product name'], 'iso-8859-1', errors='replace'))
                loader.add_value('price', Decimal(row['Price']) + Decimal(row['Shipping cost']))
                loader.add_value('shipping_cost', row['Shipping cost'])
                stock = int(row['Stock availability']) if row['Stock availability'] else 0
                loader.add_value('stock', stock)
                loader.add_value('url', row['Product page URL'])
                loader.add_value('image_url', row['Image URL'])
                item = loader.load_item()

                metadata = FragranceDirectMeta()
                metadata['rrp'] = row['RRP']
                metadata['cost_price'] = row['Cost']
                metadata['promotion'] = ''#row['Promotional Message']
                metadata['ean'] = row['EAN']
                metadata['price_on_site'] = row['Price']
                metadata['minimum_sell'] = Decimal(row['Cost']) * Decimal('1.2') * Decimal('1.35')
                metadata['cost_price_exc_vat'] = Decimal(row['Cost']) / Decimal('1.2')
                metadata['price_exc_vat'] = Decimal(row['Price']) / Decimal('1.2')
                item['metadata'] = metadata

                yield item



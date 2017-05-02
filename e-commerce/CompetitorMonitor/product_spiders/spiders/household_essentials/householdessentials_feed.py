import os
import csv
import paramiko
from scrapy.spider import BaseSpider
from scrapy.http import Request

from utils import excel_to_csv
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

from cStringIO import StringIO

from householdessentialsitem import HouseholdEssentialsMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class HouseholdEssentialsSpider(BaseSpider):
    name = 'householdessentials-feed'

    filename = os.path.join(HERE, 'householdessentials_products.csv')
    start_urls = ('file://' + filename,)

    def start_requests(self):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "n4pyn8vU"
        username = "household"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()
        last = get_last_file(files)
        if last.filename.endswith('.xlsx'):
            sftp.get(last.filename, 'household_products.xlsx')
            excel_to_csv('household_products.xlsx', self.filename)
        else:
            sftp.get(last.filename, self.filename)
        if last.filename != 'householdessentials_products.csv':
            sftp.put(self.filename, 'householdessentials_products.csv')

        yield Request(self.start_urls[0], callback=self.parse)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['Item Number'].lower())
            loader.add_value('sku', row['Item Number'])
            loader.add_value('brand', row.get('Brand'))
            loader.add_value('category', row['Category'].decode('utf8'))
            loader.add_value('name', row['Item  Description'].decode('utf8'))
            loader.add_value('price', row['MSRP'])
            loader.add_value('image_url', row['Image URL'])
            item =  loader.load_item()
            metadata = HouseholdEssentialsMeta()
            metadata['upc'] = row['UPC']
            metadata['amazon_asin'] = row['Amazon ASIN']
            metadata['target_tcin'] = row['Target TCIN']
            metadata['walmart_code'] = row['Walmart #']
            metadata['wayfair_code'] = row['Wayfair']
            item['metadata'] = metadata
            yield item

def get_last_file(files):
    exts = ('xlsx', '.csv')
    last = None
    for f in files:
        if ((last == None and f.filename[-4:] in exts) or
            (f.filename[-4:] in exts and
             f.st_mtime > last.st_mtime)):
            last = f
    return last

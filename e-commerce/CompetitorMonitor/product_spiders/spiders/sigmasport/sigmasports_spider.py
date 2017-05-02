import os
import re
import csv
import xlrd
import paramiko

from scrapy.spider import BaseSpider

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.primary_spider import PrimarySpider
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

from scrapy import log

from sigmasportitems import SigmaSportMeta, extract_exc_vat_price

HERE = os.path.abspath(os.path.dirname(__file__))

class SigmaSportSpider(PrimarySpider):
    name = 'sigmasport-sigmasport.co.uk-feed'
    allowed_domains = ['sigmasport.co.uk']
    start_urls = ('http://www.sigmasport.co.uk',)

    csv_file = 'sigmasport.co.uk_crawl.csv'

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "5tdsR23z"
        username = "sigmasport"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        last = get_last_file("SigmaFirst1000Products", "xlsx", files)
        file_path = HERE+'/SigmaFirst1000Products.xlsx'
        sftp.get(last.filename, file_path)

        wb = xlrd.open_workbook(file_path)
        sh = wb.sheet_by_name('Sheet1')

        product_ids = {}
        for rownum in xrange(sh.nrows):
            if rownum < 1:
                continue
            row = sh.row_slice(rownum)
            product_id = row[2].value
            if row[2].ctype == 2:
                product_id = str(int(row[2].value))
            product_ids[product_id.replace('-GB', '')] = []

        last = get_last_file("feedspark", "tsv", files)

        file_path = HERE+'/feedspark.tsv'
        sftp.get(last.filename, file_path)
        with open(file_path) as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                product_id = row['id'].replace('-GB', '').upper().strip()
                
                if product_id in product_ids.keys():
                    loader = ProductLoader(response=response, item=Product())
                    loader.add_value('sku', row['code'].replace('-gb', '').replace('-GB', ''))
                    categories = row['mapped_category'].split('>')
                    for category in categories:
                        loader.add_value('category', category.strip().encode('utf-8'))
                    loader.add_value('brand', row['brand'].encode('utf-8'))
                    name = [row['title']]
                    if row['colour']:
                        name.append(row['colour'])
                    if row['size']:
                        name.append(row['size'])
                    try:
                        loader.add_value('name', " ".join(name).encode('utf-8'))
                    except:
                        loader.add_value('name', " ".join(name).decode('utf-8'))
                    loader.add_value('price', row['price'])
                    loader.add_value('image_url', row['image_link'])
                    loader.add_value('url', row['link'])
                    loader.add_value('identifier', row['id'])
                    if row['availability'].lower() == 'out of stock':
                        loader.add_value('stock', 0)

                    if loader.get_output_value('price')<10:
                        loader.add_value('shipping_cost', 1.99)
 
                    product = loader.load_item()
                    metadata = SigmaSportMeta()
                    metadata['mpn'] = row['mpn']
                    metadata['item_group_number'] = row['item_group_id']
                    metadata['cost_price'] = row.get('cost_price', '0.00').replace(' GBP', '')
                    metadata['price_exc_vat'] = extract_exc_vat_price(product)
                    metadata['sku_gb'] = str(product['sku']) + '-GB'if product.get('sku', None) else ''
                    product['metadata'] = metadata
                    
                    # Check if the products have different prices
                    collected_products = product_ids[product_id]
                    prices = []
                    for collected_product in collected_products:
                        prices.append(product['price'])

                    if product['price'] not in prices:
                        product_ids[product_id].append(product)

            # Collects all the products for each name
            for name, products in product_ids.iteritems():
                for product in products:
                    yield product

def get_last_file(start_with, ends_with, files):
    """
    Returns the most recent file, for the file name which starts with start_with

    :param start_with: the file name has this form start_with + date
    :param files: files list sftp.listdir_attr
    """
    last = None
    for f in files:
        if ((last == None and start_with in f.filename and 
             f.filename.endswith(ends_with)) or 
            (start_with in f.filename and f.filename.endswith(ends_with) and 
             f.st_mtime > last.st_mtime)):
            last = f
    return last

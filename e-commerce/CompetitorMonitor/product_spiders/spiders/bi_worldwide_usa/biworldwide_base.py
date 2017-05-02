import os
import csv
import xlrd
import paramiko

from scrapy.spider import BaseSpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO
from product_spiders.spiders.bi_worldwide_usa.biworldwideitem import BIWordlwideMeta

from product_spiders.utils import extract_price
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))

class BIWBaseSpider(BaseSpider):
    name = ''
    start_urls = ('http://www.biworldwide.com',)
    file_start_with = ''
    xls_file_path = ''
    csv_file_path = ''

    identifiers = []
    image_url_key = None
    tag_keys = dict()

    def parse(self, response):

        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "p02SgdLU"
        username = "biw"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        last = get_last_file(self.file_start_with, files)

        sftp.get(last.filename, self.xls_file_path)

        # Convert XLXS file to CSV
        excel_to_csv(self.xls_file_path, self.csv_file_path)

        with open(self.csv_file_path) as f:
            reader = csv.DictReader(f, delimiter=',')
            for row in reader:

                if row['BI ProductID'].lower() in self.identifiers:
                    continue

                self.identifiers.append(row['BI ProductID'].lower())
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('identifier', row['BI ProductID'])
                loader.add_value('sku', row['BI ProductID'])
                loader.add_value('category', unicode(row['BI Product Grp'], errors='ignore'))
                loader.add_value('category', unicode(row['BI CategoryGroup'], errors='ignore'))
                loader.add_value('name', unicode(row['BI ProductName'], errors='ignore'))
                loader.add_value('price', extract_price(row['BI ListPrice']))
                loader.add_value('shipping_cost', extract_price(row['BI Shipping']))
                loader.add_value('brand', unicode(row['BI Brand'], errors='ignore'))
                loader.add_value('url', '')
                if self.image_url_key:
                    image_url = row.get(self.image_url_key)
                    if image_url.lower() != 'na':
                        loader.add_value('image_url', image_url)
                else:
                    loader.add_value('image_url', '')
                product = loader.load_item()
                metadata = BIWordlwideMeta()
                metadata['dropship_fee'] =  unicode(row['BI Dropship Fee'], errors='ignore')
                metadata['est_tax'] =  unicode(row['BI Est Tax'], errors='ignore')
                metadata['ship_weight'] =  unicode(row['BI ship Wt'], errors='ignore')
                metadata['product_group'] =  unicode(row['BI Product Grp'], errors='ignore')
                metadata['upc'] =  unicode(row['BI UPC #'], errors='ignore')
                metadata['mpn'] =  unicode(row['BI Model'], errors='ignore')
                metadata['item_group'] = unicode(row.get('BI ItemGroup', ''), errors='ignore')
                for meta_key, feed_key in self.tag_keys.items():
                    tag = unicode(row.get(feed_key, ''), errors='ignore')
                    tag = tag if tag != u'NA' else u'N/A'
                    metadata[meta_key] = tag
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
             f.filename.endswith('.xlsx')) or 
            (start_with in f.filename and f.filename.endswith('.xlsx') and 
             f.st_mtime > last.st_mtime)):
            last = f
    return last


def excel_to_csv(xls_filename, csv_filename):
    wb = xlrd.open_workbook(xls_filename)
    sh = wb.sheet_by_index(0)
    csv_file = open(csv_filename, 'wb')
    wr = csv.writer(csv_file, quoting=csv.QUOTE_ALL)

    for rownum in xrange(sh.nrows):
        wr.writerow([unicode(val).encode('utf8') for val in sh.row_values(rownum)])

    csv_file.close()

import os
import csv
import json
import xlrd
import paramiko

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.item import Item, Field
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


from product_spiders.utils import extract_price, excel_to_csv
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


class ZyroFeedMeta(Item):
    style_code = Field()
    upc = Field()


class ZyroSpider(BaseSpider):
    name = 'zyro-zyro.co.uk'
    start_urls = ('http://www.zyro.co.uk',)
    allowed_domains = ['zyro.co.uk']
    file_start_with = 'CM SKU '
    handle_httpstatus_list = [404]
    xls_file_path = 'zyro_feed.xlsx'
    csv_file_path = 'zyro_feed.csv'

    identifiers = []

    def parse(self, response):

        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "6k3DFs2x"
        username = "zyro"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        last = get_last_file(self.file_start_with, files)

        sftp.get(last.filename, self.xls_file_path)

        # Convert XLXS file to CSV
        excel_to_csv(self.xls_file_path, self.csv_file_path)

        with open(self.csv_file_path) as f:
            reader = UnicodeDictReader(f) # csv.DictReader(f, delimiter=',')
            for row in reader:
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('identifier', row['SKU'])
                loader.add_value('sku', row['SKU'])
                loader.add_value('name', row['Name'])
                loader.add_value('price', row['SRP'])
                loader.add_value('brand', row['Brand'])
                loader.add_value('category', row['ProductCategory'])
                loader.add_value('image_url', row['ImageUrl'])
                loader.add_value('url', row['ProductUrl'])
                product = loader.load_item()
                metadata = ZyroFeedMeta()
                metadata['style_code'] =  row['Stylecode']
                metadata['upc'] =  row['UPC']
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

def _excel_to_csv(xls_filename, csv_filename):
    wb = xlrd.open_workbook(xls_filename)
    sh = wb.sheet_by_index(0)
    csv_file = open(csv_filename, 'wb')
    wr = csv.writer(csv_file, quoting=csv.QUOTE_ALL)

    for rownum in xrange(sh.nrows):
        row = sh.row(rownum)
        wr.writerow([unicode(col.value).encode('utf8') for col in sh.row(rownum)])

    csv_file.close()

def UnicodeDictReader(utf8_data):
    csv_reader = csv.DictReader(utf8_data)
    for row in csv_reader:
        yield {key: unicode(value, 'utf-8') for key, value in row.iteritems()}

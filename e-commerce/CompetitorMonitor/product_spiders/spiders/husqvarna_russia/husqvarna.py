import os
import csv
import xlrd
import paramiko

from scrapy.spider import BaseSpider

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class HusqvarnaSpider(BaseSpider):
    name = 'husqvarna_russian-husqvarna.com'
    allowed_domains = ['husqvarna.com']
    start_urls = ('http://www.husqvarna.com',)

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "g45dR5dz"
        username = "husqvarna"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        #last = get_last_file("husqvarna_russia", files)
        file_path = HERE+'/husqvarna.xlsx'
        #sftp.get(last.filename, file_path)

        wb = xlrd.open_workbook(file_path)
        sh = wb.sheet_by_name('Products')

        for rownum in xrange(sh.nrows):
            if rownum < 2:
                continue
            
            row = sh.row_values(rownum)
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('sku', row[2])
            loader.add_value('category', row[0])
            loader.add_value('brand', row[1])
            if isinstance(row[2], float):
                name = row[5] + " " + str(int(row[2]))
            else:
                name = row[5] + " " + row[2]
            loader.add_value('name', name)
            loader.add_value('price', row[6])
            loader.add_value('image_url', row[3])
            loader.add_value('identifier', row[2])
            yield loader.load_item()

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

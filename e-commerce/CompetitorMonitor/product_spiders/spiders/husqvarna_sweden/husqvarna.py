import os
import csv
import xlrd
import paramiko

from scrapy.spider import BaseSpider

from utils import extract_price, excel_to_csv
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class HusqvarnaSpider(BaseSpider):
    name = 'husqvarna_sweden-husqvarna.com'
    allowed_domains = ['husqvarna.com']
    start_urls = ('http://www.husqvarna.com',)

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "g45dR5dz"
        username = "husqvarna"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        last = get_last_file("husqvarna_sweden", files)

        file_path_xlsx = HERE+'/husqvarna_feed.xlsx'
        sftp.get(last.filename, file_path_xlsx)
        file_path_csv = HERE + '/husqvarna_feed.csv'
        
        excel_to_csv(file_path_xlsx, file_path_csv)
        with open (file_path_csv) as csv_file:
            next(csv_file)
            reader = csv.DictReader(csv_file)
            for row in reader:
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('sku', row['Model'].decode('utf-8'))
                loader.add_value('category', row['Category'].decode('utf-8'))
                loader.add_value('brand', row['Brand'].decode('utf-8'))
                loader.add_value('name', row['Local language name'].decode('utf-8'))
                loader.add_value('price', row['RRP'])
                loader.add_value('image_url', row['Image'])
                loader.add_value('identifier', row['Model'].decode('utf-8'))
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

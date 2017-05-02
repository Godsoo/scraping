# -*- coding: utf-8 -*-
import os
import csv
import xlrd
import paramiko

from scrapy.spider import BaseSpider

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT
from product_spiders.utils import excel_to_csv

HERE = os.path.abspath(os.path.dirname(__file__))

class HusqvarnaSpider(BaseSpider):
    name = 'husqvarna.com'
    allowed_domains = ['husqvarna.com']
    start_urls = ('http://www.husqvarna.com',)

    extracted_products = []

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "g45dR5dz"
        username = "husqvarna"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        last = get_last_file("husqvarna_france", files)
        file_path = HERE + '/husqvarna_feed.xlsx'
        csv_file_path = HERE + '/husqvarna_feed.csv'
        sftp.get(last.filename, file_path)
        excel_to_csv(file_path, csv_file_path)

        csv_file = open(csv_file_path)
        next(csv_file)
        csv_reader = csv.DictReader(csv_file)

        for row in csv_reader:
           
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('sku', row['Model'].decode('utf-8'))
            loader.add_value('category', row['Category'].decode('utf-8'))
            loader.add_value('brand', row['Brand'].decode('utf-8'))
            loader.add_value('name', row['Local language name'].decode('utf-8'))
            loader.add_value('price', row['RRP2016'])
            loader.add_value('image_url', row['Image'])
            loader.add_value('identifier', row['PNC'])
            if row['RRP2016']:
                yield loader.load_item()
        
        csv_file.close()

def get_last_file(start_with, files):
    """
    Returns the most recent file, for the file name which starts with start_with

    :param start_with: the file name has this form start_with  date
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

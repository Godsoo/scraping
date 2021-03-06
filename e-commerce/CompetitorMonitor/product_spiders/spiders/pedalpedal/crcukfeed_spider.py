import os
import re
import csv
import shutil
import zipfile
import paramiko
from datetime import datetime

import xml.etree.ElementTree as et
from product_spiders.base_spiders.primary_spider import PrimarySpider
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.spiders.BeautifulSoup import BeautifulSoup

from product_spiders.utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class CrcUKSpider(PrimarySpider):
    name = 'chainreactioncycles.com-feed'
    allowed_domains = ['chainreactioncycles.com']
    start_urls = ('http://www.chainreactioncycles.com',)

    errors = []
   
    handle_httpstatus_list = [403, 400, 503]
    csv_file = 'crcukfeed.csv'

    def parse(self, response):
        base_url = get_base_url(response)
        
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "baquieL6"
        username = "crc"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        last = get_last_file("CRC_PRICEFEED_UK", files)

        date_file = datetime.fromtimestamp(last.st_mtime) 
        hours_diff = (datetime.now() - date_file).total_seconds() / 3600

        # Check file updates
        if hours_diff >= 72:
            self.errors.append('WARNING: No Update for 3 days')
        '''
        usa_file = get_last_file("CRC_PRICEFEED_USA", files)
        if usa_file:
            usa_date_file = datetime.fromtimestamp(usa_file.st_mtime) 
            hours_diff = (datetime.now() - usa_date_file).total_seconds() / 3600

            if hours_diff <= 32:
                self.errors.append('WARNING: Invalid File Name, USA feed uploaded recently')
        '''
        zip_path = HERE+'/CRC_PRICEFEED_UK.zip'
        xml_path = HERE+'/CRC_PRICEFEED_UK.xml'
 
        sftp.get(last.filename, zip_path)

        unzip(zip_path, xml_path)

        xmlfeed_sku = ''
        with open(xml_path) as f:
            xmlfeed_sku = f.read()

        sku_prices = {}
        tree = et.fromstring(xmlfeed_sku)
        for item in tree.find('priceList[@id="UKRP"]').find('prices').findall('price'):
            sku = item.find('skuId').text 
            price = item.find('listPrice').text
            sku_prices[sku] = price


        last = get_last_file("PriceMonitorHandler", files)

        zip_path = HERE+'/PriceMonitorHandler.zip'
        xml_path = HERE+'/PriceMonitorHandler.xml'

        sftp.get(last.filename, zip_path)

        unzip(zip_path, xml_path)
        
        xmlfeed_products = ''
        with open(xml_path) as f:
            xmlfeed_products = f.read()

        sku_products = {}
        tree = et.fromstring(xmlfeed_products)
        for item in tree.find('skus').findall('sku'):
            sku_products[item.find('skuID').text] = {'identifier': item.find('skuID').text, 
                                                     'category': item.find('CategoryDescription').text, 
                                                     'brand': item.find('BrandDescription').text, 
                                                     'image_url': item.find('ImageURL').text, 
                                                     'url': item.find('ProductURL').text, 
                                                     'name': item.find('SkuDescription').text,
                                                     'sku': item.find('skuID').text,
                                                     'stock': item.find('SkuQuantity').text}

        for sku, price in sku_prices.iteritems():
            try:
                product = sku_products[sku]
            except KeyError:
                log.msg('SKU not found:' + sku)
                continue

            product['price'] = price
            product = Product(product)

            loader = ProductLoader(response=response, item=product)
            yield loader.load_item()

def unzip(zip_path, dest_path):
    zfile = zipfile.ZipFile(zip_path)
    for name in zfile.namelist():
        (dir_name, file_name) = os.path.split(name)
        if file_name == '':
            # directory
            new_dir = dest_path
            if not os.path.exists(new_dir):
                os.mkdir(new_dir)
        else:
            # file
            fd = open(dest_path, 'wb')
            fd.write(zfile.read(name))
            fd.close()
    zfile.close()

def get_last_file(file_string, files):
    """
    Returns the most recent file, for the file name which starts with file_string

    :param file_string: the file name has this form file_string + date
    :param files: files list sftp.listdir_attr
    """
    last = None
    for f in files:
        if ((last == None and file_string in f.filename and 
             f.filename.endswith('.zip')) or 
            (file_string in f.filename and f.filename.endswith('.zip') and 
             f.st_mtime > last.st_mtime)):
            last = f
    return last

# -*- coding: utf-8 -*-

import os
import csv
import xlrd
from ftplib import FTP
from scrapy.spider import BaseSpider
from scrapy.http import Request

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

from findelitems import FindelMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class FindelSpider(BaseSpider):
    name = 'findel-findel-education.co.uk'

    findel_filename = os.path.join(HERE, 'Findel.xlsx')
    start_urls = ['http://www.findel-education.co.uk']

    ftp_server = 'ftp.findel-education.co.uk'
    username = 'C0mpPr1ce'
    password = 'FtPU$3r'

    def parse(self, response):

        ftp = FTP(self.ftp_server)
        ftp.login(self.username, self.password)

        ftp.retrbinary('RETR Findel.xlsx', open(self.findel_filename, 'wb').write)

        wb = xlrd.open_workbook(self.findel_filename)
        sh = wb.sheet_by_index(0)

        for rownum in xrange(sh.nrows):
            if rownum < 1:
                continue

            row = sh.row(rownum)

            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row[1].value.lower())
            loader.add_value('sku', row[1].value)
            try:
                brand = str(row[6].value).decode('utf8')
            except UnicodeEncodeError:
                brand = row[6].value

            brand = brand if brand != '0.0' and brand != '0' else ''
            loader.add_value('brand', brand)

            categories = [row[10].value, row[11].value, row[12].value]
            for category in categories:
                category = str(category).decode('utf8')
                if category != '0.0' and category != '0':
                    loader.add_value('category', category)

            loader.add_value('name', row[3].value)
            name = loader.get_output_value('name')
            if name == '42':
                continue

            loader.add_value('price', row[14].value)
            loader.add_value('url', row[15].value)

            try:
                image_url = str(row[16].value)
            except UnicodeEncodeError:
                image_url = row[16].value
     
            image_url = image_url if 'http' in image_url else ''

            loader.add_value('image_url', image_url)
            item = loader.load_item()
            metadata = FindelMeta()
            metadata['cost_price'] = row[13].value
            item['metadata'] = metadata
            yield item

        sh = wb.sheet_by_index(1)
        for rownum in xrange(sh.nrows):
            if rownum < 1:
                continue

            row = sh.row(rownum)

            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row[1].value.lower())
            loader.add_value('sku', row[1].value)

            try:
                brand = str(row[6].value).decode('utf8')
            except UnicodeEncodeError:
                brand = row[6].value

            brand = brand if brand != '0.0' and brand != '0' else ''
            loader.add_value('brand', brand)

            categories = [row[7].value, row[8].value, row[9].value]
            for category in categories:
                category = str(category).decode('utf8')
                if category != '0.0' and category != '0':
                    loader.add_value('category', category)

            loader.add_value('name', row[3].value)
            name = loader.get_output_value('name')
            if name == '42':
                continue

            loader.add_value('price', row[14].value)
            loader.add_value('url', row[15].value)
            try:
                image_url = str(row[16].value)
            except UnicodeEncodeError:
                image_url = row[16].value
     
            image_url = image_url if 'http' in image_url else ''
            loader.add_value('image_url', image_url)
            item = loader.load_item()
            metadata = FindelMeta()
            metadata['cost_price'] = row[13].value
            item['metadata'] = metadata
            yield item

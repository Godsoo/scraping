import os
import re
import csv
import ftplib
import cStringIO
from scrapy.spider import BaseSpider

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class Reader:
   def __init__(self):
     self.data = ""
   def __call__(self,s):
      self.data += s

class OfficespotUKSpider(BaseSpider):
    name = 'officespot.ie-ireland'
    allowed_domains = ['officespot.ie']
    start_urls = ('http://www.officespot.ie',)

    def parse(self, response):
        ftp = ftplib.FTP("81.17.254.85")
        ftp.login("f111449.cmonitor", "cv7GBz+-C!fd4t6J")
        r = Reader()
        ftp.retrbinary('RETR cm-price-ie.csv', r)
        reader = csv.DictReader(cStringIO.StringIO(r.data.replace('\,','\.')))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['sku'].lower())
            loader.add_value('sku', row['sku'])
            loader.add_value('url', row.get('url_path'))
            loader.add_value('category', row.get('category'))
            loader.add_value('brand', row.get('brand'))
            loader.add_value('image_url', row.get('image_url'))
            loader.add_value('name', row['name'].decode('utf8').replace('\.', ','))
            loader.add_value('price', round(float(row['price']), 2))
            yield loader.load_item()

        

    



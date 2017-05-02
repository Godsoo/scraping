import os
from scrapy.spider import BaseSpider
import xlrd
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

from scrapy import log


class LogitechdeSpider(BaseSpider):
    name = 'logitech.de'
    base_url = "http://logitech.de/"
    allowed_domains = ['logitech.de', 'logitech.com']
    start_urls = [base_url]

    def parse(self, response):
        file_path = HERE + '/logitech_de.xlsx'
        wb = xlrd.open_workbook(file_path)
        sh = wb.sheet_by_name('Sheet1')

        for rownum in xrange(sh.nrows):
            if rownum < 2:
                continue
            row = sh.row_values(rownum)
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('category', row[1])
            loader.add_value('brand', row[2])
            loader.add_value('image_url', row[3])
            loader.add_value('sku', row[4])
            identifier = row[5] if row[5].strip() != 'NA' else row[4]
            identifier = identifier if identifier else row[4]
            loader.add_value('identifier', identifier)
            loader.add_value('name', row[7].replace(' EER Orient Packaging', '').replace(' Central Packaging', ''))
            price = extract_price(str(row[8]))
            if not price:
                price = '0.0'
                loader.add_value('stock', 0)
            loader.add_value('price', price)
            yield loader.load_item()

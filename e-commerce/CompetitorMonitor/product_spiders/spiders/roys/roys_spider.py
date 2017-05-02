import os
import xlrd

from scrapy.spider import BaseSpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class RoysSpider(BaseSpider):
    name = 'roys-roys.co.uk'

    start_urls = ['http://www.roys.co.uk']


    def parse(self, response):
        filename = os.path.join(HERE, 'RoysData.xlsx')
        wb = xlrd.open_workbook(filename)
        sh = wb.sheet_by_name('Sheet1')

        def convert_value(value):
            try:
                result = str(float(value)).strip().replace('.0', '')
            except:
                result = str(value).strip()
            return result

        for rownum in xrange(sh.nrows):
            if rownum < 1:
                continue
            
            row = sh.row_values(rownum)
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', row[6])
            loader.add_value('name', str(row[9]).strip() + ' ' + str(row[10]).strip())
            price = row[11]
            loader.add_value('price', price)
            loader.add_value('sku', row[6])
            loader.add_value('brand', row[7])
            loader.add_value('category', row[1])
            loader.add_value('category', row[3])
            loader.add_value('category', row[5])
            if loader.get_output_value('price')<=39.99:
                loader.add_value('shipping_cost', 4.99)
            yield loader.load_item()

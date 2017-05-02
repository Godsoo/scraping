import os
import xlrd

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin
from decimal import Decimal
from scrapy import log
import copy

HERE = os.path.abspath(os.path.dirname(__file__))


class ProcurementIntlSpider(BaseSpider):
    name = 'procurement_intl'
    start_urls = ['http://www.impro-int.com/']
    allowed_domains    = ['johnlewis.com', 'impro-int.com']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        file_path = HERE + '/ProductsToTest.xlsx'
        wb = xlrd.open_workbook(file_path)
        sh = wb.sheet_by_index(0)

        for rownum in xrange(sh.nrows):
            if rownum < 1:
                continue
            row = sh.row_values(rownum)
            url = row[15]
            loader = ProductLoader(item=Product(), selector=Product())
            loader.add_value('identifier', row[0])
            loader.add_value('name', row[1])
            loader.add_value('brand', row[2])
            loader.add_value('category', [row[3], row[4]])
            loader.add_value('price', row[7])
            loader.add_value('image_url', row[11])
            meta = {'manufacture_code': row[14]}
            loader.add_value('metadata', meta)
            product = loader.load_item()
            product['metadata'] = {'12nc': row[2], 'barcode_eu': row[7]}

            yield product

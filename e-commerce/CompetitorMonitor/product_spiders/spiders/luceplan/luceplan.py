import os
import xlrd

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class LuceplanSpider(BaseSpider):
    name = 'luceplan_file'
    start_urls = ['http://www.luceplan.com']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        file_path = HERE + '/luceplan_products.xlsx'
        wb = xlrd.open_workbook(file_path)
        sh = wb.sheet_by_index(0)

        for rownum in xrange(sh.nrows):
            if rownum < 2:
                continue
            row = sh.row_values(rownum)

            loader = ProductLoader(item=Product(), selector=Product())
            loader.add_value('identifier', row[0])
            loader.add_value('name', "%s %s" % (row[3], row[6]))
            loader.add_value('category', row[5])
            loader.add_value('brand', "Luceplan")
            loader.add_value('sku', row[7])
            loader.add_value('price', row[8])
            loader.add_value('stock', 1)
            product = loader.load_item()
            product['metadata'] = {'12nc': row[2], 'barcode_eu': row[7]}
            yield product

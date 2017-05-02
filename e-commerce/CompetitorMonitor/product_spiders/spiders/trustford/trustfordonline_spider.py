import os
import csv
import xlrd
import paramiko

from scrapy import log

from scrapy.spider import BaseSpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))

class TrustFordOnLineSpider(BaseSpider):
    name = 'trustfordonline.co.uk'

    filename = os.path.join(HERE, 'trustford_products.csv')
    start_urls = ('file://' + filename,)


    def parse(self, response):

        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "p12Hgr17"
        username = "trustford"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        last = get_last_file(files)

        file_path = HERE+'/trustford_products.xls'
        sftp.get(last.filename, file_path)

        wb = xlrd.open_workbook(file_path)
        sh = wb.sheet_by_name('Vehicle Listing & Pricing')

        def convert_value(value):
            try:
                result = str(float(value)).strip().replace('.0', '')
            except:
                result = str(value).strip()
            return result

        for rownum in xrange(sh.nrows):
            row = sh.row_values(rownum)
            if row[0]:
                product_name = ' '.join(map(convert_value, [row[1], row[2], row[3], row[4], row[5],row[6]]))

                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('identifier', convert_value(row[0]))
                loader.add_value('name', product_name)
                loader.add_value('price', row[7])
                loader.add_value('category', row[1])
                loader.add_value('brand', 'Ford')

                yield loader.load_item()

def get_last_file(files):
    """
    Returns the most recent file, for the file name which starts with start_with

    :param start_with: the file name has this form start_with + date
    :param files: files list sftp.listdir_attr
    """
    last = None
    for f in files:
        if ((last == None and f.filename.endswith('.xls')) or
            (f.filename.endswith('.xls') and f.st_mtime > last.st_mtime)):
            last = f
    return last

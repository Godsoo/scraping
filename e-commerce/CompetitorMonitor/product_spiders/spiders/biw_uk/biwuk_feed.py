import os
import csv
import xlrd
import paramiko

from scrapy.spider import BaseSpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from product_spiders.spiders.bi_worldwide_usa.biworldwideitem import BIWordlwideMeta

from cStringIO import StringIO

from product_spiders.utils import extract_price
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))

class BIWUKSpider(BaseSpider):
    name = 'biw-uk-feed'
    start_urls = ('http://www.biworldwide.com',)


    def parse(self, response):

        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "p02SgdLU"
        username = "biw"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        last = get_last_file("BI UK File", files)

        file_path = HERE + '/biwuk_products.csv'
        sftp.get(last.filename, file_path)

        with open(file_path) as f:
            reader = csv.DictReader(f, delimiter=',')
            for row in reader:
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('identifier', row['BI UK ProductID'])
                loader.add_value('sku', row['BI UK ProductID'])
                categories = unicode(row.get('BI UK CategoryGroup'), errors='ignore').replace('>>', '>').replace("'", "").split('>')
                for category in categories:
                    loader.add_value('category', category.strip())
                loader.add_value('name', unicode(row['BI UK ProductName'], errors='ignore'))
                loader.add_value('price', extract_price(row['BI UK Delivered Price']))
                loader.add_value('shipping_cost', extract_price(row['BI UK Shipping']))
                loader.add_value('brand', row['BI UK Brand'])
                loader.add_value('url', '')
                loader.add_value('image_url', row['BI UK ImgURL'])
                product = loader.load_item()
                metadata = BIWordlwideMeta()
                metadata['dropship_fee'] =  unicode(row['BI UK Dropship Fee'], errors='ignore')
                metadata['est_tax'] =  unicode(row['BI UK Est Tax'], errors='ignore')
                metadata['ship_weight'] =  unicode(row['BI UK ship Wt'], errors='ignore')
                metadata['product_group'] =  unicode(row['BI UK Product Grp'], errors='ignore')
                metadata['upc'] =  unicode(row['BI UK UPC #'], errors='ignore')
                metadata['mpn'] =  unicode(row['BI UK Model'], errors='ignore')
                product['metadata'] = metadata
                yield product

def get_last_file(start_with, files):
    """
    Returns the most recent file, for the file name which starts with start_with

    :param start_with: the file name has this form start_with + date
    :param files: files list sftp.listdir_attr
    """
    last = None
    for f in files:
        if ((last == None and start_with in f.filename and 
             f.filename.endswith('.csv')) or 
            (start_with in f.filename and f.filename.endswith('.csv') and 
             f.st_mtime > last.st_mtime)):
            last = f
    return last

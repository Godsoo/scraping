import os
import csv
import paramiko
from scrapy.spider import BaseSpider

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

from product_spiders.spiders.navico_amer.navicoitem import NavicoMeta

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))

class NavicoSpider_Emea(BaseSpider):
    name = 'navico-emea-navico.com'

    start_urls = ('http://www.navico.com',)

    file_name = 'navico_products.csv'

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "A7Ct8rLX07n"
        username = "navico"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        csv_file = HERE+'/navico_feed.csv'

        sftp.get(self.file_name, csv_file)

        with open(csv_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('identifier', row['code'].lower())
                loader.add_value('sku', row['code'])
                loader.add_value('brand', row['brand'])
                loader.add_value('category', 'Chartplotter/Fishfinder')
                loader.add_value('name', row['description'].decode('utf8'))
                loader.add_value('price', 0)
                product = loader.load_item()
                metadata = NavicoMeta()
                metadata['screen_size'] = row['screen size']
                product['metadata'] = metadata
                yield product

import os
import csv
import paramiko
from scrapy.spider import BaseSpider

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

from navicoitem import NavicoMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class NavicoSpider(BaseSpider):
    name = 'navico-amer-navico.com'

    navico_filename = os.path.join(HERE, 'navico_products.csv')
    start_urls = ('file://' + navico_filename,)

    file_name = 'navico_feed_amer.csv'

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "A7Ct8rLX07n"
        username = "navico"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        csv_file = os.path.join(HERE, 'navico_feed_navico.csv')

        sftp.get(self.file_name, csv_file)

        products = {}

        with open(csv_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                loader = ProductLoader(response=response, item=Product())
                identifier = row['Product.BaseSKU'].lower()
                loader.add_value('identifier', identifier)
                loader.add_value('sku', identifier)
                loader.add_value('brand', row['Brand.CUST'])
                loader.add_value('category', row['ProductCategory.CUST'])
                loader.add_value('name', row['Product.Name'])
                price = row['MAP'] or row[' MRP ']
                loader.add_value('price', price)
                product = loader.load_item()
                metadata = NavicoMeta()
                metadata['sub_category'] = row['Product.SubCategory']
                metadata['is_map'] = bool(row['MAP'])
                metadata['is_mrp'] = bool(row[' MRP '])
                metadata['MAP'] = True
                product['metadata'] = metadata
                products[identifier] = product

        remote_filename = 'navico_screensize_products.csv'
        data_filepath_local = os.path.join(HERE, 'navico_screensize_products_navico.csv')

        sftp.get(remote_filename, data_filepath_local)

        with open(data_filepath_local) as f:
            reader = csv.DictReader(f, delimiter=',')
            for i, row in enumerate(reader, 1):
                identifier = row['Manufacturer Part Number'].lower()
                if identifier in products:
                    product = products[identifier]
                else:
                    loader = ProductLoader(response=response, item=Product())
                    loader.add_value('identifier', identifier)
                    loader.add_value('sku', identifier)
                    loader.add_value('brand', row['Brand'])
                    loader.add_value('category', row['Category'])
                    loader.add_value('name', row['Description'])
                    loader.add_value('price', 0)
                    product = loader.load_item()
                    metadata = NavicoMeta()
                    product['metadata'] = metadata
                product['metadata']['screen_size'] = row['Category']
                products[identifier] = product

        for product in products.values():
            yield product

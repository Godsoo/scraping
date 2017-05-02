import os
import paramiko
from scrapy.spider import BaseSpider
from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))

from scrapy.item import Item, Field

class MusicroomMeta(Item):
    cost_price = Field()
    net_retail_price = Field()

class MusicroomFeedSpider(BaseSpider):
    name = 'musicroom.com-feed'
    allowed_domains = ['musicroom.com']
    start_urls = ('http://www.musicroom.com',)

    handle_httpstatus_list = [403, 400, 503]

    errors = []

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "bu9xaiGh"
        username = "msg"
        filename = 'IntelligentEye.txt'
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.get(filename, HERE + '/' + filename)

        fields = ['UniqueProductCode', 'isbn', 'ean', 'upc', 'ProductName', 'PriceGBP', 'ProductPageURL', 'Brand',
                  'Category', 'ImageURL', 'Stock', 'ShippingCost', 'NetRetailPrice', 'CostPrice']
        fields2 = ['UniqueProductCode', 'isbn', 'ean', 'upc', 'ProductName', 'Temp1', 'PriceGBP', 'ProductPageURL',
                   'Brand', 'Category', 'ImageURL', 'Stock', 'ShippingCost', 'NetRetailPrice', 'CostPrice']
        with open(os.path.join(HERE, filename)) as f:
            for i, line in enumerate(f, 1):
                line = line.decode('cp865', 'ignore')
                values = line.split('\t')
                if len(fields) == len(values):
                    data = dict(zip(fields, values))
                elif len(fields2) == len(values):
                    data = dict(zip(fields2, values))
                else:
                    msg = "Incorrect number of fields on line: %d" % i
                    self.log("[ERROR] %s" % msg)
                    self.errors.append(msg)
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('identifier', data['UniqueProductCode'])
                loader.add_value('sku', data['UniqueProductCode'])
                loader.add_value('name', data['ProductName'])
                loader.add_value('price', extract_price(data['PriceGBP']))
                loader.add_value('url', data['ProductPageURL'])
                loader.add_value('image_url', data['ImageURL'])
                loader.add_value('brand', data['Brand'])
                loader.add_value('category', data['Category'])
                loader.add_value('shipping_cost', data['ShippingCost'])
                loader.add_value('stock', data['Stock'])
                item = loader.load_item()
                item['sku'] = item['sku'].upper()

                metadata = MusicroomMeta()
                metadata['cost_price'] = data['CostPrice'].strip()
                metadata['net_retail_price'] = data['NetRetailPrice'].strip()

                item['metadata'] = metadata

                yield item
import os
import csv
import ftplib
import paramiko
import cStringIO
from scrapy.spider import BaseSpider
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))

class Reader:
   def __init__(self):
     self.data = ""
   def __call__(self, s):
      self.data += s

class TapOutletSpider(BaseSpider):
    name = 'tapoutlet.co.uk'
    allowed_domains = ['tapoutlet.co.uk']
    start_urls = ('http://www.tapoutlet.co.uk',)
    
    ignore_urls = ['saniflo-1046-1-sanicom-1046-heavy-duty-pump',
                   'saniflo-1003-saniplus-macerator-small-bore-sanitary-system',
                   'greenstar-he-ii-vertical-flue-kit']
    products = []
    prod_check =  {}

    image_base = 'http://91833e325c7627016055-a071f48db8cee70132a641662b939b02.r30.cf3.rackcdn.com/catalog/product/cache/4/image/325x/9df78eab33525d08d6e5fb8d27136e95/'

    handle_httpstatus_list = [403, 400, 503]

    def __init__(self, *args, **kwargs):
        super(TapOutletSpider, self).__init__(*args, **kwargs)
        #dispatcher.connect(self.spider_closed, signals.spider_closed)
        with open(os.path.join(HERE, 'fIntelligenteye10K.csv')) as f:
           reader = csv.DictReader(f)
           for row in reader:
               self.products.append(' '.join((row['manufacturer'], row['manufacturer_sku'])).replace(' ', '_').lower())

    def parse(self, response):
        base_url = get_base_url(response)

        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "ieL5Beeh"
        username = "tapoutlet"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        file_path = HERE+'/Intelligenteye_export.csv'
        sftp.get('Intelligenteye_export.csv', file_path)

        with open(file_path) as f:
            reader = csv.DictReader(cStringIO.StringIO(f.read().replace('\,', '\.')))
            for row in reader:
                identifier = ' '.join((row['Brand'], row['SKU'])).replace(' ', '_').lower()
                if identifier in self.products and row['Product Page URL'] and row['Product Page URL'] not in self.ignore_urls:
                    loader = ProductLoader(response=response, item=Product())
                    loader.add_value('identifier', identifier)
                    loader.add_value('sku', row['SKU'].replace(' ', ''))
                    loader.add_value('name', row['Product name'].decode('utf8').replace('\.', ','))
                    price = 0
                    if row['price']:
                        price = round(float(row['price']), 2)

                    loader.add_value('price', price)
                    loader.add_value('url', urljoin_rfc(base_url, row['Product Page URL']+'.html'))
                    loader.add_value('image_url', urljoin_rfc(self.image_base, row['image URL']))
                    loader.add_value('brand', row['Brand'])
                    loader.add_value('category', row['Category'])
                    if price < 99 and row['Shipping'] in ('small', 'medium'):
                        loader.add_value('shipping_cost', 4.95)
                    elif row['Shipping'] == 'large' and price < 299:
                        loader.add_value('shipping_cost', 34.95)
                    self.prod_check[identifier] = True
                 
                    yield loader.load_item()

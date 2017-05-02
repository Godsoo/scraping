import os
import csv
import paramiko
from decimal import Decimal
from scrapy import Spider, Request
from scrapy.item import Item, Field
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import DATA_DIR


HERE = os.path.abspath(os.path.dirname(__file__))
PRODUCTS_FILENAME = 'bensons_cost_prices_updated.csv'


SFTP_HOST = 'sftp.competitormonitor.com'
SFTP_PORT = 2222
SFTP_USER = 'bensons'
SFTP_PSWD = '3F3aPbWb'


class Meta(Item):
    net_price = Field()
    cost_price = Field()


class BedshedSpider(Spider):
    name = 'bedshed.co.uk'
    allowed_domains = ['bedshed.co.uk']
    start_urls = ['http://www.bedshed.co.uk/']

    def start_requests(self):
        yield Request(self.start_urls[0], meta={'handle_httpstatus_all': True})

    def _get_all_products_filename(self):
        filename = None
        if hasattr(self, 'website_id'):
            filename = os.path.join(DATA_DIR, '%s_all_products.csv' % self.website_id)
        return filename

    def _get_prev_crawl_filename(self):
        filename = None
        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
        return filename

    def parse(self, response):
        local_filename = os.path.join(HERE, PRODUCTS_FILENAME)

        try:
            transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
            transport.connect(username=SFTP_USER, password=SFTP_PSWD)
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.get(PRODUCTS_FILENAME, local_filename)
            transport.close()
        except Exception as e:
            self.log('SFTP ERROR => %r' % e)
            try:
                transport.close()
            except:
                pass
        else:
            to_ignore = []
            with open(os.path.join(HERE, 'to_ignore.csv')) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    to_ignore.append(row['identifier'])

            products_data = {}
            prev_filename = self._get_prev_crawl_filename()
            if prev_filename and os.path.exists(prev_filename):
                with open(prev_filename) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        products_data[row['identifier']] = row.copy()
            all_filename = self._get_all_products_filename()
            if all_filename and os.path.exists(all_filename):
                with open(all_filename) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['identifier'] not in products_data:
                            products_data[row['identifier']] = row.copy()

            with open(local_filename) as f:
                # Using reader instead DictReader because some columns have no name
                reader = csv.reader(f)
                reader.next()  # header
                for row in reader:
                    sku = row[0]
                    if sku in to_ignore:
                        continue
                    product_data = products_data.get(sku, {})
                    loader = ProductLoader(item=Product(), response=response)
                    loader.add_value('sku', sku)
                    loader.add_value('identifier', sku)
                    loader.add_value('price', row[23])
                    loader.add_value('name', product_data.get('name', row[1]))
                    loader.add_value('category', product_data.get('category', row[7]))
                    loader.add_value('brand', product_data.get('brand', ''))
                    loader.add_value('shipping_cost', product_data.get('shipping_cost', '0'))
                    loader.add_value('url', product_data.get('url', ''))
                    loader.add_value('image_url', product_data.get('image_url', ''))
                    price = Decimal(loader.get_output_value('price'))
                    net_price = price / Decimal('1.2')

                    p = loader.load_item()
                    meta_ = Meta()
                    meta_['net_price'] = str(net_price)
                    meta_['cost_price'] = extract_price(row[24])
                    p['metadata'] = meta_
                    yield p

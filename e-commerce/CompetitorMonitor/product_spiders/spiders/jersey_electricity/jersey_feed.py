# -*- coding: utf-8 -*-
import csv
import os
import paramiko

from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

from jersey_electricity_items import JerseyElectricityMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class JerseyElectricitySpider(BaseSpider):
    name = 'jec.co.uk-feed'
    allowed_domains = ['powerhouse.je']
    start_urls = ('http://www.powerhouse.je/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        username = 'jerseyelectricity'
        password = 'pTF1iUhP'
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        filepath = 'intelligent_eye_feed.csv'
        localpath = os.path.join(HERE, 'intelligent_eye_feed.csv')
        sftp.get(filepath, localpath)
        sftp.close()
        transport.close()

        with open(localpath) as f:
            reader = csv.DictReader(f)
            for row in reader:
                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('sku', row['REFERENCE'])
                loader.add_value('brand', row['BRAND'])
                loader.add_value('category', row['PRODUCT_CATEGORY'].split(' > '))
                loader.add_value('name', row['TITLE'].decode('utf8', 'ignore'))
                loader.add_value('price', row['PRICE'] or '0')
                loader.add_value('shipping_cost', row['SHIPPING_COST'])
                loader.add_value('image_url', row['IMAGE_LINK'])
                loader.add_value('url', row['LINK'])
                loader.add_value('identifier', row['REFERENCE'])
                if row['AVAILABILITY'].lower()=="out of stock":
                    loader.add_value('stock', 0)
                item = loader.load_item()

                metadata = JerseyElectricityMeta()
                metadata['cost_price'] = row['COST_PRICE']
                metadata['cost_price_exc_vat'] = Decimal(row['COST_PRICE']) / Decimal('1.05')
                item['metadata'] = metadata
                yield item

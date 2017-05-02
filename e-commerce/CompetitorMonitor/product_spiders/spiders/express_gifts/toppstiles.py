"""
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/3976-express-gifts---new-site---topps-tiles/details

!IMPORTANT the JSON in the product pages seems to be broken (e.g. missing commas)
"""
import re
import demjson
import paramiko
import os
import csv
import json
from decimal import Decimal
from tempfile import NamedTemporaryFile

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

HERE = os.path.abspath(os.path.dirname(__file__))


class ToppsTilesSpider(BaseSpider):
    name = 'expressgifts-toppstiles.co.uk'
    allowed_domains = ['toppstiles.co.uk']
    start_urls = ['http://www.toppstiles.co.uk']

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "jqh3aMrK"
        username = "expressgifts"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        f = NamedTemporaryFile(delete=True, suffix='.csv', prefix='expressgifts_toppstiles_')
        sftp.get('express_gifts_flat_file.csv', f.name)

        with open(f.name) as csv_f:
            reader = csv.DictReader(csv_f)
            for row in reader:
                url = row['TOPPS_TILES'].strip()
                if url:
                    yield Request(url, dont_filter=True, callback=self.parse_product, meta={'row': row})

        f.close()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        data = hxs.select('//script[contains(text(),"dataLayer =")]/text()').re('dataLayer = (.*);')[0]
        data = data.replace('""', '","')
        data = json.loads(data)[0]

        data = data['ecommerce']['detail']['products'][0]

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('name', data['name'])
        loader.add_value('url', response.url)
        loader.add_value('identifier', response.meta.get('row').get('PRODUCT_NUMBER'))
        loader.add_xpath('image_url', '//img[@class="cloudzoom"]/@data-cloudzoom', re='zoomImage:(.*?)\',')
        loader.add_value('price', data['price'])
        loader.add_value('sku', response.meta.get('row').get('PRODUCT_NUMBER'))
        loader.add_value('brand', data['brand'])
        price = loader.get_output_value('price')
        if price and Decimal(price) < Decimal('250.0'):
            loader.add_value('shipping_cost', '20.00')
        stock = hxs.select('.//span[@class="avail_instock"]/text()').extract()
        stock = stock and ('specially ordered' in stock[0].lower() or 'in stock' in stock[0].lower())
        if not stock:
            loader.add_value('stock', 0)


        for category in hxs.select('//div[@class="crumbTrail"]/a/text()')[1:].extract():
            loader.add_value('category', category)

        yield loader.load_item()

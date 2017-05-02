"""
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/3960-express-gifts---new-site---smyths/details#
"""
import re
import json
import paramiko
import os
import csv
from tempfile import NamedTemporaryFile
from decimal import Decimal

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


class SmythsToysSpider(BaseSpider):
    name = 'expressgifts-smythstoys.com'
    allowed_domains = ['smythstoys.com']
    start_urls = ['http://www.smythstoys.com/uk/en-gb/']

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "jqh3aMrK"
        username = "expressgifts"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        f = NamedTemporaryFile(delete=True, suffix='.csv', prefix='expressgifts_smyths_')
        sftp.get('express_gifts_flat_file.csv', f.name)

        with open(f.name) as csv_f:
            reader = csv.DictReader(csv_f)
            for row in reader:
                url = row['SMYTHS'].strip()
                if url:
                    yield Request(url, dont_filter=True, callback=self.parse_product, meta={'row': row})

        f.close()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('name', './/span[@itemprop="name"]/text()')
        loader.add_value('url', response.url)
        loader.add_value('identifier', response.meta.get('row').get('PRODUCT_NUMBER'))
        loader.add_xpath('image_url', '//img[@itemprop="image"]/@src')
        loader.add_xpath('price', './/span[@class="pricing"]//span[@class="price"]/text()')
        loader.add_value('sku', response.meta.get('row').get('PRODUCT_NUMBER'))
        stock = hxs.select('//div[@class="stock-status"]//span[@class="in-stock"]')
        if not stock:
            loader.add_value('stock', 0)

        data = hxs.select('//div[@class="ega-proddetails"]/@data-event').extract()
        if data:
            data = json.loads(data[0])
            loader.add_value('brand', data['brand'])

        price = loader.get_output_value('price')
        if price and Decimal(price) < Decimal('29.00'):
            loader.add_value('shipping_cost', '2.99')

        for category in hxs.select('//li[contains(@itemtype,"Breadcrumb")]/a/span/text()')[1:].extract():
            loader.add_value('category', category)

        yield loader.load_item()

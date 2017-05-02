"""
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/3973-express-gifts---spider-copy---tesco/details#
"""
import csv
import os
import logging
import re
from datetime import datetime
import paramiko
from tempfile import NamedTemporaryFile

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

import json


class TescoComSpider(BaseSpider):
    name = 'expressgifts-tesco.com'
    allowed_domains = ['tesco.com']
    start_urls = (
        'http://www.tesco.com/direct/',
    )

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "jqh3aMrK"
        username = "expressgifts"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        f = NamedTemporaryFile(delete=True, suffix='.csv', prefix='expressgifts_tesco_')
        sftp.get('express_gifts_flat_file.csv', f.name)

        with open(f.name) as csv_f:
            reader = csv.DictReader(csv_f)
            for row in reader:
                url = row['TESCO'].strip()
                if url:
                    yield Request(url, dont_filter=True, callback=self.parse_product, meta={'row': row})

        f.close()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        url = response.url
        brand = hxs.select('//div[@itemprop="brand"]/li/a/strong/span/text()').extract()
        l = ProductLoader(item=Product(), response=response)

        name = hxs.select('//h1[@class="page-title"]/text()').extract()
        if not name:
            logging.error("ERROR! NO NAME! %s" % url)
            return
        name = name[0].strip()
        l.add_value('name', name)

        price = hxs.select('//*[@itemprop="price"]/text()').extract()
        if not price:
            logging.error("ERROR! NO PRICE! %s %s" % (url, name))
            price = ''
        l.add_value('price', price)
        l.add_value('identifier', response.meta.get('row').get('PRODUCT_NUMBER'))
        l.add_value('url', url)

        for category in hxs.select('//div[@id="breadcrumb"]//li[not (@class="last")]//a/span/text()')[1:].extract():
            l.add_value('category', category)
        l.add_value('brand', brand[0].strip() if brand else '')

        l.add_value('sku', response.meta.get('row').get('PRODUCT_NUMBER'))

        image_url = hxs.select('//div[contains(@class, "static-product-image")]/img/@src').extract()
        if image_url:
            l.add_value('image_url', image_url[0])

        yield l.load_item()

"""
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/3967-express-gifts---new-site---sonic-direct/details#
"""
import re
import demjson
import paramiko
import os
import csv
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


class SonicDirectSpider(BaseSpider):
    name = 'expressgifts-sonicdirect.co.uk'
    allowed_domains = ['sonicdirect.co.uk']
    start_urls = ['http://www.sonicdirect.co.uk']

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "jqh3aMrK"
        username = "expressgifts"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        f = NamedTemporaryFile(delete=True, suffix='.csv', prefix='expressgifts_sonicdirect_')
        sftp.get('express_gifts_flat_file.csv', f.name)

        with open(f.name) as csv_f:
            reader = csv.DictReader(csv_f)
            for row in reader:
                url = row['SONIC_DIRECT'].strip()
                if url:
                    yield Request(url, dont_filter=True, callback=self.parse_product, meta={'row': row})

        f.close()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('name', './/h1[@itemprop="name"]/text()')
        loader.add_value('url', response.url)
        loader.add_value('identifier', response.meta.get('row').get('PRODUCT_NUMBER'))
        loader.add_xpath('image_url', '//div[contains(@class,"product-detail-group")]//meta[@itemprop="image"]/@content')
        loader.add_xpath('price', '//li[@itemprop="price"]/text()')
        loader.add_value('sku', response.meta.get('row').get('PRODUCT_NUMBER'))
        loader.add_xpath('brand', '//div[contains(@class,"product-detail-group")]//div[@class="brand-logo"]/img/@alt')


        for category in hxs.select('//span[contains(@itemtype,"Breadcrumb")]/a/text()').extract():
            loader.add_value('category', category)

        yield loader.load_item()

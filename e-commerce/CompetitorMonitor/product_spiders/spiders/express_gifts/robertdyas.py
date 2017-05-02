"""
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/3959-express-gifts---new-site---robert-dyas/details#
"""
import re
import demjson
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


class RobertDyasSpider(BaseSpider):
    name = 'expressgifts-robertdyas.co.uk'
    allowed_domains = ['robertdyas.co.uk']
    start_urls = ['http://www.robertdyas.co.uk']

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "jqh3aMrK"
        username = "expressgifts"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        f = NamedTemporaryFile(delete=True, suffix='.csv', prefix='expressgifts_robertdyas_')
        sftp.get('express_gifts_flat_file.csv', f.name)

        with open(f.name) as csv_f:
            reader = csv.DictReader(csv_f)
            for row in reader:
                url = row['ROBERT_DYAS'].strip()
                if url:
                    yield Request(url, dont_filter=True, callback=self.parse_product, meta={'row': row})

        f.close()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('url', response.url)
        loader.add_value('identifier', response.meta.get('row').get('PRODUCT_NUMBER'))
        loader.add_xpath('image_url', '//img[@id="image-main"]/@src')
        loader.add_xpath('price', '//div[contains(@class,"product-view")]//span[@class="regular-price"]//span[@class="price"]/text()')
        loader.add_value('sku', response.meta.get('row').get('PRODUCT_NUMBER'))
        out_of_stock = hxs.select('//div[contains(@class,"product-view")]//p[@class="availability out-of-stock"]')
        if out_of_stock:
            loader.add_value('stock', 0)

        data = hxs.select('//script[contains(text(),"ec:addProduct")]/text()').extract()
        if data:
            data = data[0].replace('\n', '').replace('\r', '')
            data = re.search('addProduct\', (.*?)\);', data).group(1)
            data = demjson.decode(data)
            loader.add_value('name', data['name'])
            loader.add_value('brand', data['brand'])
            loader.add_value('category', data['category'])

        else:
            name = hxs.select('//div[@class="product-name"]/span[@class="h1"]/text()').extract()
            brand = hxs.select('//div[@id="title-brand-right"]/div/a/img/@alt').re('View more by (.*)')
            loader.add_value('name', name)
            loader.add_value('brand', brand)


        price = loader.get_output_value('price')
        if price and Decimal(price) < Decimal('50.00'):
            loader.add_value('shipping_cost', '3.95')


        yield loader.load_item()

"""
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/3975-express-gifts---new-site---the-range/details
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
    name = 'expressgifts-therange.co.uk'
    allowed_domains = ['therange.co.uk']
    start_urls = ['http://www.therange.co.uk']

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "jqh3aMrK"
        username = "expressgifts"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        f = NamedTemporaryFile(delete=True, suffix='.csv', prefix='expressgifts_therange_')
        sftp.get('express_gifts_flat_file.csv', f.name)

        with open(f.name) as csv_f:
            reader = csv.DictReader(csv_f)
            for row in reader:
                url = row['THE_RANGE'].strip()
                if url:
                    yield Request(url, callback=self.parse_product, meta={'row': row})

        f.close()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        main_name = re.search('ecommerce.*name\': \'(.*?)\'', response.body, re.DOTALL).group(1)
        main_price = re.search('ecommerce.*price\': \'(.*?)\'', response.body, re.DOTALL).group(1)
        brand = re.search('ecommerce.*?brand\': \'(.*?)\'', response.body, re.DOTALL).group(1)

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('name', main_name)
        loader.add_value('url', response.url)
        loader.add_value('price', response.url)
        loader.add_xpath('image_url', '//meta[@property="og:image"]/@content')
        loader.add_value('identifier', response.meta.get('row').get('PRODUCT_NUMBER'))
        loader.add_value('sku', response.meta.get('row').get('PRODUCT_NUMBER'))
        loader.add_value('brand', brand)
        for category in hxs.select('//div[@id="breadcrumb"]/ul[@id="crumbs"]/li/a/text()')[1:].extract():
            loader.add_value('category', category)

        options = hxs.select('//select[@name="ProductID" and @id="select_size"]/option')
        for option in options:
            identifier = option.select('./@value')[0].extract()
            loader.replace_value('identifier', identifier)

            option_name, option_price = option.select('./text()')[0].extract().strip().split(' - ')
            loader.replace_value('name', '{} {}'.format(main_name, option_name))
            loader.replace_value('price', option_price)

            yield loader.load_item()

        if not options:
            yield loader.load_item()

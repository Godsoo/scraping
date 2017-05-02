import re
import os
import csv
import paramiko

import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


class DuplaySpider(BaseSpider):
    name = 'expressgifts-duplay.co.uk'
    allowed_domains = ['duplay.co.uk']

    start_urls = ['http://www.duplay.co.uk']

    def parse(self, response):
        base_url = get_base_url(response)

        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "jqh3aMrK"
        username = "expressgifts"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()
        
        file_path = HERE + '/express_gifts_flat_file.csv'
        sftp.get('express_gifts_flat_file.csv', file_path)


        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row['DUPLAY'].strip()
                if url:
                    yield Request(url, callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
 
        row = response.meta['row']

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('identifier', row['PRODUCT_NUMBER'])
        loader.add_value('sku', row['PRODUCT_NUMBER'])
        loader.add_xpath('brand', '//span[@class="brand"]/text()')
        categories = hxs.select('//ul[@class="crumb"]/li/a/text()').extract()
        loader.add_value('category', categories)
        loader.add_xpath('name', '//h2[@itemprop="name"]/text()')
        loader.add_xpath('price', '//span[@class="list_price"]/text()')
        loader.add_value('url', response.url)
        loader.add_xpath('image_url', '//img[@id="imyimage"]/@src')
        out_of_stock = hxs.select('//meta[@itemprop="availability" and contains(@content, "OutOfStock")]')
        if out_of_stock:
            loader.add_value('stock', 0)
        yield loader.load_item()

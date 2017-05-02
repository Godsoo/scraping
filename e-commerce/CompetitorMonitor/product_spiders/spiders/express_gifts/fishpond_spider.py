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


class FishPondSpider(BaseSpider):
    name = 'expressgifts-fishpond.co.uk'
    allowed_domains = ['fishpond.co.uk']

    start_urls = ['http://www.fishpond.co.uk']

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
                url = row['FISH_POND.CO.UK'].strip()
                if url:
                    yield Request(url, callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
 
        row = response.meta['row']

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('identifier', row['PRODUCT_NUMBER'])
        loader.add_value('sku', row['PRODUCT_NUMBER'])
        loader.add_xpath('brand', '//tr[th[contains(text(), "Brand")]]/td/a/text()')
        categories = hxs.select('//span[@class="breadcrumbLarge"]/div/a/span/text()').extract()
        loader.add_value('category', categories)
        loader.add_xpath('name', '//span[@itemprop="name"]/text()')
        loader.add_xpath('price', '//meta[@itemprop="price"]/@content')
        loader.add_value('url', response.url)
        loader.add_xpath('image_url', '//span[@class="img"]/img/@src')
        out_of_stock = hxs.select('//meta[@itemprop="availability" and contains(@content, "OutOfStock")]')
        if out_of_stock:
            loader.add_value('stock', 0)
        yield loader.load_item()

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


class BmStoresSpider(BaseSpider):
    name = 'expressgifts-bmstores.co.uk'
    allowed_domains = ['bmstores.co.uk']

    start_urls = ['http://www.bmstores.co.uk']

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
                url = row['B&M_BARGAINS'].strip()
                if url:
                    yield Request(url, callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
 
        row = response.meta['row']

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('identifier', row['PRODUCT_NUMBER'])
        loader.add_value('sku', row['PRODUCT_NUMBER'])
        loader.add_xpath('brand', '//div[@class="product-detail-logo"]/a/img/@alt')
        categories = hxs.select('//ul[@id="breadcrumbs"]/li/a/text()').extract()[1:-1]
        loader.add_value('category', categories)
        loader.add_xpath('name', '//h1[@class="content-title"]/text()')

        price = hxs.select('//article[@class="aside-content"]/h2/span/text()').extract()
        if not price:
            price = hxs.select('//article[@class="aside-content"]/h2/text()').extract()
        loader.add_value('price', price)

        loader.add_value('url', response.url)
        image_url = hxs.select('//div[@class="product-detail-feature-img"]/a/img/@src').extract()
        image_url = urljoin_rfc(get_base_url(response), image_url[0]) if image_url else ''
        loader.add_value('image_url', image_url)
        yield loader.load_item()

import re
import os
import csv
import json
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


class KiddiCareSpider(BaseSpider):
    name = 'expressgifts-kiddicare.com'
    allowed_domains = ['kiddicare.com']

    start_urls = ['http://www.kiddicare.com/']

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
                url = row['KIDDICARE'].strip()
                if url:
                    yield Request(url, callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
 
        row = response.meta['row']
 
        product_data = re.findall("qubit_product_list = (.*);", response.body)
        product_data = json.loads(product_data[0]) if product_data else None

        if product_data:
            product_data = product_data.values()[0]

            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['PRODUCT_NUMBER'])
            loader.add_value('sku', row['PRODUCT_NUMBER'])
            loader.add_value('brand', product_data['kc_brand'])
            categories = hxs.select('//a[@class="breadcrumb"]/text()').extract()[1:]
            loader.add_value('category', categories)
            loader.add_value('name', product_data['item_name'])
            loader.add_value('price', product_data['unit_sale_price'])
            loader.add_value('url', response.url)
            image_url = hxs.select('//meta[@name="sailthru.image.full"]/@content').extract()
            image_url = 'http://' + image_url[0] if image_url else ''
            loader.add_value('image_url', image_url)
            if product_data['stock'] <= 0:
                loader.add_value('stock', 0)
            yield loader.load_item()

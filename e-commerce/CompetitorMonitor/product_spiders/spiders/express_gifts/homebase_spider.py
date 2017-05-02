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


class HomebaseSpider(BaseSpider):
    name = 'expressgifts-homebase.co.uk'
    allowed_domains = ['homebase.co.uk']

    start_urls = ['http://www.homebase.co.uk/']

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
                url = row['HOMEBASE'].strip()
                if url:
                    yield Request(url, callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
 
        row = response.meta['row']

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('identifier', row['PRODUCT_NUMBER'])
        loader.add_value('sku', row['PRODUCT_NUMBER'])

        categories = ''
        loader.add_value('category', categories)
        loader.add_xpath('name', '//h1/span[@itemprop="name"]/text()')
        loader.add_xpath('price', '//span[@itemprop="price"]/text()')
        loader.add_value('url', response.url)

        product_brand = ''
        brands = hxs.select('//div[contains(h5/text(), "Shop by brand")]//ul/li/a/text()').extract()
        for brand in brands:
            if ''.join(brand.split()).upper().strip() in ''.join(loader.get_output_value('name').split()).upper():
                product_brand = brand
                break
        loader.add_value('brand', product_brand)

        image_url = hxs.select('//div[@class="product_detail-left-image-wrapper"]//img/@src').extract()
        image_url = 'http://' + image_url[0] if image_url else ''
        loader.add_value('image_url', image_url)
        yield loader.load_item()

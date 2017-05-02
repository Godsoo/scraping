import re
import json
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


class JDWilliamsSpider(BaseSpider):
    name = 'expressgifts-jdwilliams.co.uk'
    allowed_domains = ['jdwilliams.co.uk']

    start_urls = ['http://www.jdwilliams.co.uk/']

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
                url = row['JD_WILLIAMS'].strip()
                if url:
                    yield Request(url, callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
 
        row = response.meta['row']

        json_data = re.search('var tagDataLayer =(.*);', response.body).group(1)
            
        product_info = json.loads(json_data)['ProductInfo']['websiteOfferedOptions'][0]

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('identifier', row['PRODUCT_NUMBER'])
        loader.add_value('sku', row['PRODUCT_NUMBER'])
        loader.add_value('brand', '')
        categories = ''
        loader.add_value('category', categories)
        name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0]
        loader.add_value('name', name + ' ' + product_info['color'])
        loader.add_value('price', product_info['price']['amountAsDouble'])
        loader.add_value('url', response.url)
        image_url = hxs.select('//meta[@property="og:image"]/@content').extract()
        image_url = image_url[0].strip() if image_url else ''
        loader.add_value('image_url', image_url)
        if product_info['outOfStock']:
            loader.add_value('stock', 0)
        yield loader.load_item()

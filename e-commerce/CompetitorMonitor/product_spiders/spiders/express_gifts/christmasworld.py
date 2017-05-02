from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin
from scrapy.utils.response import get_base_url

import os
import paramiko
import csv

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))

class UKChristmasWorld(BaseSpider):
    name = "ukchristmasworld.com"
    allowed_domains = ['ukchristmasworld.com']
    
    def start_requests(self):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "jqh3aMrK"
        username = "expressgifts"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        file_path = HERE + '/express_gifts_flat_file.csv'
        sftp.get('express_gifts_flat_file.csv', file_path)
        
        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row['CHRISTMAS_WORLD'].strip()
                if url:
                    yield Request(url, callback=self.parse_product, meta={'id': row['PRODUCT_NUMBER']})
            
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(selector=hxs, item=Product())
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//div[@id="BuyBoxArea"]//h1[@itemprop="name"]/text()')
        loader.add_value('identifier', response.meta['id'])
        loader.add_value('sku', response.meta['id'])
        loader.add_xpath('price', '//span[@itemprop="price"]/text()')
        stock = 1 if hxs.select('//span[text()="In Stock"]') else 0
        loader.add_value('stock', stock)
        loader.add_xpath('category', '//div[@class="breadcrumb"]/a[position()>1]/text()')
        loader.add_xpath('brand', '//td[text()="Brand"]/../td[2]/text()')
        loader.add_xpath('image_url', '//img[@class="js-main-image"]/@src')
        product = loader.load_item()
        if product['price'] < 40:
            product['shipping_cost'] = 4.95
        yield product
        
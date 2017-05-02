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


class My1styearsSpider(BaseSpider):
    name = 'expressgifts-my1styears.com'
    allowed_domains = ['my1styears.com']

    start_urls = ['http://www.my1styears.com']

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
                url = row['MY1STYEARS'].strip()
                if url:
                    yield Request(url, callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        row = response.meta['row']

        try:
            category = hxs.select('//div[contains(@class, "breadcrumbs")]//ul/li/a/text()').extract()[1:]
        except IndexError:
            category = ''
        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()


        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('identifier', row['PRODUCT_NUMBER'])
        product_loader.add_value('sku', row['PRODUCT_NUMBER'])
        name = hxs.select('//div[contains(@class, "product-name")]/h1/text()').extract()[0].strip()
        product_loader.add_value('name', name)
        price = hxs.select('//div[@class="product-shop"]//span[@class="regular-price"]/span[@class="price"]/text()').extract()[0]
        product_loader.add_value('price', price)
        product_loader.add_value('url', response.url)
        product_loader.add_value('category', category)
        product_loader.add_value('image_url', image_url)
        product_loader.add_value('brand', '')
        in_stock = hxs.select('//p[contains(@class, "availability")]/span[contains(@class, "icon-in-stock")]')
        if not in_stock:
            product_loader.add_value('stock', 0)
        if product_loader.get_output_value('price')<40:
            product_loader.add_value('shipping_cost', 3.00)
        yield product_loader.load_item()	

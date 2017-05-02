import re
import os
import csv
import paramiko
from decimal import Decimal

import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


class AllBeautySpider(BaseSpider):
    name = 'expressgifts-allbeauty.com'
    allowed_domains = ['allbeauty.com']

    start_urls = ['http://www.allbeauty.com']
    cookies={'locale':'GBP%2C48%2C0%2CEN'}

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
                url = row['ALL_BEAUTY'].strip()
                if url:
                    yield Request(url, callback=self.parse_product,  cookies=self.cookies, meta={'row': row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        row = response.meta['row']

        if not hxs.select('//div[@class="productDetail"]'):
            return

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_value('sku', row['PRODUCT_NUMBER'])
        product_loader.add_value('identifier', row['PRODUCT_NUMBER'])
        product_loader.add_xpath('name', u'//div[@class="productDescription"]/h3/text()|//div[@class="productDescription"]/h4/text()')
        product_loader.add_xpath('brand', u'//div[@class="productDescription"]/h2/text()')
        if hxs.select('//input[contains(@class, "purchaseButton")]'):
            product_loader.add_value('stock', '1')
        product_loader.add_xpath('category', '//p[@id="breadCrumbs"]/a[position() > 1]/text()')
        img = hxs.select(u'//img[@class="productImage"]/@src').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        product_loader.add_xpath('price', './/span[@class="ourPrice"]/text()')
        item = product_loader.load_item()

        if item['price'] < 25:
            item['shipping_cost'] = Decimal('1.95')

        yield item

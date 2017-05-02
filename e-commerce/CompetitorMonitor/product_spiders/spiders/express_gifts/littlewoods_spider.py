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


class LittlewoodsSpider(BaseSpider):
    name = 'expressgifts-littlewoods.com'
    allowed_domains = ['littlewoods.com']

    start_urls = ['http://www.littlewoods.com']

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
                url = row['LITTLEWOODS'].strip()
                if url:
                    yield Request(url, callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        row = response.meta['row']
        
        loader = ProductLoader(item=Product(), response=response)
        name = ''.join(hxs.select('//h1[@class="productHeading"]//text()').extract())
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        brand = re.findall('brand: "(.*)",', response.body)
        brand = brand[0].strip() if brand else ''
        loader.add_value('brand', brand)
        category = hxs.select('//ul[@class="breadcrumbList"]/li/a/text()').extract()[1:]
        loader.add_value('category', category)
        loader.add_value('sku', row['PRODUCT_NUMBER'])
        loader.add_value('identifier', row['PRODUCT_NUMBER'])
        image_url = hxs.select('//div[@id="amp-originalImage"]/img/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])

        price = ''.join(hxs.select('//div[@class="priceNow"]//text()').extract())
        loader.add_value('price', price)

        out_of_stock = 'IN STOCK' not in ''.join(hxs.select('//meta[@property="product:availability"]/@content').extract()).upper()
        if out_of_stock:
            loader.add_value('stock', '0')

        yield loader.load_item()


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

from product_spiders.utils import extract_price
from copy import deepcopy

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


class MatalanSpider(BaseSpider):
    name = 'expressgifts-matalan.co.uk'
    allowed_domains = ['matalan.co.uk']

    start_urls = ['http://www.matalan.co.uk']

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
                url = row['MATALAN'].strip()
                if url:
                    yield Request(url, dont_filter=True, callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
 
        row = response.meta['row']

        loader = ProductLoader(response=response, item=Product())
        identifier = re.findall('"id": "(.*)"', response.body)
        loader.add_value('identifier', identifier[0])
        loader.add_value('sku', identifier[0])
        loader.add_value('brand', '')
        categories = hxs.select('//ul[contains(@class, "breadcrumb")]/li/a/span/text()').extract()
        categories = map(lambda x: x.strip(), categories)
        loader.add_value('category', categories)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        loader.add_xpath('price', '//div[@class="product-info-main"]//li[@class="price"]/text()')
        loader.add_value('url', response.url)
        image_url = hxs.select('//section[@id="product-visuals"]//img[@itemprop="image"]/@src').extract()
        image_url = image_url[0] if image_url else ''
        loader.add_value('image_url', image_url)
        in_stock = hxs.select('//link[@itemprop="availability" and contains(@href, "InStock")]')
        if not in_stock:
            loader.add_value('stock', 0)

        if loader.get_output_value('price')<50:
            loader.add_value('shipping_cost', 3.95)
        item = loader.load_item()
        
        options = hxs.select('//select[@name="Size"]/option[@value!=""]')
        if options:
            for option in options:
                stock = int(option.select('@data-max').extract()[0])
                name = ''.join(option.select('text()').extract()).split(' - ')[0].strip()
                option_identifier = option.select('@value').extract()[0]
                option_item = deepcopy(item)
                option_item['identifier'] = option_identifier
                if not stock:
                    option_item['stock'] = 0
                option_item['name'] += ' ' + name
                option_item['price'] = extract_price(option.select('text()').extract()[0])
                yield option_item
        else:
            yield item
                

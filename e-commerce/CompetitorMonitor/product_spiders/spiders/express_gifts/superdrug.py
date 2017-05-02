"""
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/3972-express-gifts---spider-copy---superdrug/details#
"""
from decimal import Decimal
import os
import re
import json
import csv
import urlparse
import paramiko
from tempfile import NamedTemporaryFile

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT


HERE = os.path.abspath(os.path.dirname(__file__))

class SuperdrugSpider(BaseSpider):
    name = 'expressgifts-superdrug.com'
    allowed_domains = ['superdrug.com']

    start_urls = ['http://www.superdrug.com']

    brands = []

    def start_requests(self):
        yield Request('http://www.superdrug.com/brands/a-to-z', callback=self.parse_brands)

    
    def parse_brands(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        self.brands = hxs.select('//li[@class="brandcat"]/a/span/text()').extract()

        for start_url in self.start_urls:
            yield Request(start_url)

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "jqh3aMrK"
        username = "expressgifts"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        f = NamedTemporaryFile(delete=True, suffix='.csv', prefix='expressgifts_superdrug_')
        sftp.get('express_gifts_flat_file.csv', f.name)

        with open(f.name) as csv_f:
            reader = csv.DictReader(csv_f)
            for row in reader:
                url = row['SUPERDRUG'].strip()
                if url:
                    yield Request(url, dont_filter=True, callback=self.parse_product, meta={'row': row})

        f.close()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        colour_options = hxs.select('//ul[contains(@class, "colour-palette")]//a/@href').extract()
        for colour_option in colour_options:
            yield Request(urljoin_rfc(base_url, colour_option), callback=self.parse_product)

        loader = ProductLoader(item=Product(), response=response)

        product_name = hxs.select('//div[contains(@class, "prod-details")]//h2/text()').extract()
        product_name = product_name[0]

        product_brand = ''
        for brand in self.brands:
            if brand.upper() in product_name.upper():
                product_brand = brand
                break
       
        product_price = hxs.select('//p[contains(@class, "pricing")]/span/text()').extract()
        product_price = extract_price(product_price[0]) if product_price else '0'
       
        product_code = hxs.select('//div[contains(@class, "code")]/strong/text()').extract()[0]

        image_url = hxs.select('//a[@class="main-thumb"]/img/@src').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
        
        categories = hxs.select('//div[contains(@class, "breadcrumb")]/a[not(@href="/") and not(@class="active")]/text()').extract()
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', product_name)
        loader.add_value('url', response.url)
        loader.add_value('sku', response.meta.get('row').get('PRODUCT_NUMBER'))
        loader.add_value('identifier', product_code)
        loader.add_value('brand', product_brand)
        loader.add_value('image_url', image_url)
        loader.add_value('category', categories)
        out_of_stock = hxs.select('//form[@class="add_to_notification"]')
        if out_of_stock:
            loader.add_value('stock', 0)

        if loader.get_output_value('price')>=10:
            loader.add_value('shipping_cost', 0)
        else:
            loader.add_value('shipping_cost', 3)

        loader.add_value('price', product_price)

        yield loader.load_item()

"""
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/3979-express-gifts---new-site---world-of-wallart/details
"""
import re
import demjson
import paramiko
import os
import csv
from decimal import Decimal, ROUND_UP
from tempfile import NamedTemporaryFile

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

def format_price(price, rounding=None):
    if price is None:
        return Decimal('0.00')

    return price.quantize(Decimal('0.01'), rounding=rounding or ROUND_UP)

HERE = os.path.abspath(os.path.dirname(__file__))


class WorldOfWallartSpider(BaseSpider):
    name = 'expressgifts-worldofwallart.co.uk'
    allowed_domains = ['worldofwallart.co.uk']
    start_urls = ['http://www.worldofwallart.co.uk']

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "jqh3aMrK"
        username = "expressgifts"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        f = NamedTemporaryFile(delete=True, suffix='.csv', prefix='expressgifts_worldofwallart_')
        sftp.get('express_gifts_flat_file.csv', f.name)

        with open(f.name) as csv_f:
            reader = csv.DictReader(csv_f)
            for row in reader:
                url = row['WORLD_OF_WALL_ART'].strip()
                if url:
                    yield Request(url, dont_filter=True, callback=self.parse_product, meta={'row': row})

        f.close()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), selector=hxs)
        main_name = hxs.select('//meta[@property="og:title"]/@content')[0].extract()
        loader.add_value('name', main_name)
        loader.add_value('url', response.url)
        loader.add_value('identifier', response.meta.get('row').get('PRODUCT_NUMBER'))
        loader.add_xpath('image_url', '//meta[@property="og:image"]/@content')
        price = hxs.select('//meta[@property="product:price:amount"]/@content').extract()
        if price:
            loader.add_value('price', format_price(Decimal(price[0])))
        else:
            loader.add_value('price', '0.00')
        loader.add_value('sku', response.meta.get('row').get('PRODUCT_NUMBER'))
        loader.add_xpath('brand', '//div[@itemprop="brand"]/div[@class="Value"]/a/span/text()')
        loader.add_value('shipping_cost', '3.99')
        stock = hxs.select('//meta[@property="og:availability" and @content="instock"]')
        if not stock:
            loader.add_value('stock', 0)


        for category in hxs.select('//div[@id="ProductBreadcrumb"]/ul/li/a/text()')[1:].extract():
            loader.add_value('category', category)

        options = hxs.select('//div[@class="productOptionViewSelect"]/select/option[not(contains(text(),"Please Choose"))]/text()').extract()
        for option in options[:1]:
            loader.replace_value('name', '{} {}'.format(main_name, option))
            yield loader.load_item()

        if not options:
            yield loader.load_item()

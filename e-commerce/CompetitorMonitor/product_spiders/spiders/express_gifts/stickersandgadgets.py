"""
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/3971-express-gifts---new-site---stickers--amp--gadgets/details#
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


class StickersAndGadgetsSpider(BaseSpider):
    name = 'expressgifts-stickersandgadgets.co.uk'
    allowed_domains = ['stickersandgadgets.co.uk']
    start_urls = ['http://www.stickersandgadgets.co.uk/']

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "jqh3aMrK"
        username = "expressgifts"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        f = NamedTemporaryFile(delete=True, suffix='.csv', prefix='expressgifts_stickers_')
        sftp.get('express_gifts_flat_file.csv', f.name)

        with open(f.name) as csv_f:
            reader = csv.DictReader(csv_f)
            for row in reader:
                url = row['STICKERS_&_GADGETS'].strip()
                if url:
                    yield Request(url, dont_filter=True, callback=self.parse_product, meta={'row': row})

        f.close()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('name', '//div[contains(@class,"product-info")]//h1[@id="product-name"]/span[@itemprop="name"]/text()')
        loader.add_value('url', response.url)
        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])
            loader.add_value('image_url', image_url)
        loader.add_value('brand', 'Stickers & Gadgets')
        for category in hxs.select('//span[contains(@itemtype,"Breadcrumb")]/a/span/text()')[1:].extract():
            loader.add_value('category', category)
        loader.add_value('sku', response.meta.get('row').get('PRODUCT_NUMBER'))

        item = loader.load_item()

        reg = re.compile('ekmProductVariantData.+?(\{.+\})', re.DOTALL)
        options = hxs.select('//script/text()').re(reg)
        if options:
            options = options[0].replace('\r\n', '')
            options = re.sub(".'item8.+?}}}}", "}}", options)
            options = eval(options)
            for option in options['items']:
                if not option['selector']:
                    continue
                loader = ProductLoader(item=item, selector=hxs)
                loader.add_xpath('name', '//div[contains(@class,"product-info")]//h1[@id="product-name"]/span[@itemprop="name"]/text()')
                for attr in option['selector']:
                    loader.add_value('name', attr['value'])
                identifier = response.meta.get('row').get('PRODUCT_NUMBER') + '-' + option['properties']['item1']['value']
                loader.add_value('identifier', identifier)
                loader.add_value('price', option['properties']['item3']['innerHTML'])
                yield loader.load_item()
        else:
            loader.add_value('identifier', response.meta.get('row').get('PRODUCT_NUMBER'))

            price = hxs.select('//div[contains(@class,"product-info")]//span[@itemprop="price"]/@content').extract()
            if price:
                price = format_price(Decimal(price[0]) * Decimal('1.2'))
            else:
                price = Decimal('0.00')
            loader.add_value('price', price)

            yield loader.load_item()

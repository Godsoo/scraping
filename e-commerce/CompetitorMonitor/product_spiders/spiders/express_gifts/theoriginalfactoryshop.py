"""
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/3974-express-gifts---new-site---the-original-factory-shop/details#
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


class TheOriginalFactoryShopSpider(BaseSpider):
    name = 'expressgifts-theoriginalfactoryshop.co.uk'
    allowed_domains = ['theoriginalfactoryshop.co.uk']
    start_urls = ['http://www.theoriginalfactoryshop.co.uk/']

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "jqh3aMrK"
        username = "expressgifts"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        f = NamedTemporaryFile(delete=True, suffix='.csv', prefix='expressgifts_theoriginalfactory_')
        sftp.get('express_gifts_flat_file.csv', f.name)

        with open(f.name) as csv_f:
            reader = csv.DictReader(csv_f)
            for row in reader:
                url = row['THE_ORIGINAL_FACTORY_SHOP'].strip()
                if url:
                    yield Request(url, dont_filter=True, callback=self.parse_product, meta={'row': row})

        f.close()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('name', '//div[@itemprop="name"]/h1/text()')
        loader.add_value('url', response.url)
        loader.add_value('identifier', response.meta.get('row').get('PRODUCT_NUMBER'))
        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])
            loader.add_value('image_url', image_url)
        price = hxs.select('//div[@class="product-essential"]//div[@class="price-box"]//p[@class="special-price"]/span[@class="price"]/text()').extract()
        if not price:
            price = hxs.select('//div[@class="product-essential"]//div[@class="price-box"]//span[@class="regular-price"]/span[@class="price"]/text()').extract()
        loader.add_value('price', price)
        loader.add_value('shipping_cost', '4.99')
        loader.add_value('sku', response.meta.get('row').get('PRODUCT_NUMBER'))

        data = hxs.select('//script[contains(text(),"ec:addProduct")]/text()').extract()
        if len(data) > 1:
            data = data[1].replace('\n', '').replace('\r', '')
            data = re.search('addProduct\', (.*?)\);', data).group(1)
            data = demjson.decode(data)
            loader.add_value('brand', data['brand'])
            loader.add_value('category', data['category'])

        stock = hxs.select('//div[@class="product-essential"]//p[@class="availability in-stock"]')
        if not stock:
            loader.add_value('stock', 0)


        #for category in hxs.select('//span[contains(@itemtype,"Breadcrumb")]/a/span/text()')[1:].extract():
         #   loader.add_value('category', category)

        yield loader.load_item()

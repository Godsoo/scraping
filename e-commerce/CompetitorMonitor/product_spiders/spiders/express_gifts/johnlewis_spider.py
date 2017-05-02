import re
import os
import csv
import paramiko

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


class JohnLewisSpider(BaseSpider):
    name = 'expressgifts-johnlewis.com'
    allowed_domains = ['johnlewis.com']

    start_urls = ['http://www.johnlewis.com']

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
                url = row['JOHN_LEWIS'].strip()
                if url:
                    yield Request(url, callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
 
        row = response.meta['row']


        name = hxs.select('normalize-space(//*[@itemprop="name"]/text())').extract()[0]
        brand = ''.join(hxs.select('//div[@itemprop="brand"]/span/text()').extract()).strip()
        try:
            image_url = urljoin_rfc(base_url,
                                    hxs.select('//div[@id="prod-media-player"]'
                                               '//img/@src').extract()[0].strip())
        except IndexError:
            image_url = ''


        price = ''.join(hxs.select('//ul/li/strong[@class="price"]/text()').extract()).strip()
        if not price:
            price = ''.join(hxs.select('//span[@class="now-price"]/text()').extract()).strip()
            if not price:
                price = ''.join(hxs.select('//div[@id="prod-price"]//strong/text()').extract()).strip()
        try:
            stock = hxs.select('//div[contains(@class, "mod-stock-availability")]'
                               '//p/strong/text()').re(r'\d+')[0]
        except IndexError:
            stock = 0

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', row['PRODUCT_NUMBER'])
        loader.add_value('sku', row['PRODUCT_NUMBER'])
        loader.add_value('name', name)
        categories = hxs.select('//div[@id="breadcrumbs"]//li/a/text()').extract()[1:]
        loader.add_value('category', categories)
        loader.add_value('image_url', image_url)
        loader.add_value('brand', brand)
        loader.add_value('url', response.url)
        loader.add_value('price', price)
        loader.add_value('stock', stock)
        if loader.get_output_value('price')<50:
            loader.add_value('shipping_cost', 3.50)
         
        yield loader.load_item()


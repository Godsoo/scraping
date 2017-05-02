import os
import csv
import paramiko

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.spider import BaseSpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url

HERE = os.path.abspath(os.path.dirname(__file__))


class ExpressGiftsDiySpider(BaseSpider):
    name = 'expressgifts-diy'
    allowed_domains = ['diy.com']
    start_urls = ['http://www.diy.com']

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "jqh3aMrK"
        username = "expressgifts"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        file_path = HERE + '/express_gifts_flat_file.csv'
        sftp.get('express_gifts_flat_file.csv', file_path)

        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row['B&Q'].strip()
                if url:
                    yield Request(url, dont_filter=True, callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        row = response.meta['row']

        url = response.url
        l = ProductLoader(item=Product(), response=response)

        # name
        name = hxs.select('//h1[@class="product-title"]/text()').extract()[0].strip()
        l.add_value('name', name)

        # price
        price = hxs.select('//p[@class="price-wrap"]/strong/text()').extract()[0]
        price = extract_price(price)
        l.add_value('price', price)

        # sku
        sku = row['PRODUCT_NUMBER']
        l.add_value('sku', sku)
        l.add_value('identifier', sku)

        # category
        category = hxs.select('//ul[@itemprop="breadcrumb"]//a/text()').extract()[1:]
        if '[...]' in category:
            category.remove('[...]')
        l.add_value('category', category)

        # product image
        image_url = hxs.select('//figure[@class="main-img"]/img/@src').extract()
        if image_url:
            l.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

        # url
        l.add_value('url', url)

        out_of_stock = ''.join(hxs.select('//*[@id="cc-msg-2"]//text()').extract())
        if 'Out of stock' in out_of_stock:
            l.add_value('stock', 0)

        if price < 50:
            l.add_value('shipping_cost', 5)

        yield l.load_item()

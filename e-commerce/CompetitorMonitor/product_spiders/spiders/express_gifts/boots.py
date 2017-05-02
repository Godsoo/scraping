from decimal import Decimal
import re
import os
import demjson
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.item import Item, Field
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT
import csv
import paramiko

HERE = os.path.abspath(os.path.dirname(__file__))


class BootsMeta(Item):
    promotion = Field()
    price_exc_vat = Field()


class ExpressGiftsBootsSpider(BaseSpider):
    name = 'expressgifts-boots.com'
    allowed_domains = ['boots.com']
    start_urls = ['http://www.boots.com']

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
                url = row['BOOTS'].strip()
                if url:
                    yield Request(url, dont_filter=True, callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        options = None
        js_line = ''
        for l in response.body.split('\n'):
            if 'variants:' in l:
                js_line = l
                break

        if js_line:
            options = demjson.decode(re.search(r'variants:(.*};)?', js_line).groups()[0][:-2].strip())

        product_loader = ProductLoader(item=Product(), selector=hxs)
        row = response.meta['row']
        sku = row['PRODUCT_NUMBER']
        product_loader.add_value('sku', sku)
        product_loader.add_value('identifier', sku)
        product_loader.add_value('url', response.url)
        name = hxs.select('//span[@itemprop="name"]/text()').extract()[0]
        product_loader.add_value('name', name)
        category = hxs.select('//*[@id="breadcrumb"]//a/text()').extract()[1:-1]
        product_loader.add_value('category', category)
        img = hxs.select('//meta[@property="og:image"]/@content').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img.pop()))
        price = hxs.select('//p[@class="productOfferPrice"]/text()').extract()[0]
        price = extract_price(price)
        product_loader.add_value('price', price)
        brand = hxs.select('//*[@id="brandHeader"]/a/@href').extract()
        if brand:
            brand = brand[0].replace('/en/', '')[:-1]
            product_loader.add_value('brand', brand)
        stock = ''.join(hxs.select('//div[@class="cvos-availbility-panel"]/p/text()').extract())
        if 'Item is currently out of stock online' in stock:
            product_loader.add_value('stock', 0)
        product = product_loader.load_item()
        metadata = BootsMeta()
        prom = ''.join(hxs.select('//div[@class="productSavings"]//text()').extract())
        metadata['promotion'] = prom + ' ' + ''.join(hxs.select('//div[@class="primaryItemDeal"]//p/text()').extract())
        if product['price']:
            metadata['price_exc_vat'] = Decimal(product['price']) / Decimal('1.2')
        product['metadata'] = metadata

        yield product

        if options:
            for k, val in options.items():
                option_name = k.replace('_', ' ')
                option_product = Product(product)
                option_product['name'] = product['name'] + ' ' + option_name
                option_product['sku'] = val['productCode']
                option_product['identifier'] = val['variantId']
                option_product['price'] = extract_price(val['nowPrice'])
                if option_product.get('price'):
                    option_product['metadata']['price_exc_vat'] = Decimal(option_product['price']) / Decimal('1.2')

                yield option_product

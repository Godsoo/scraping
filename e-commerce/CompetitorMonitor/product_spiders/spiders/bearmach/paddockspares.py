"""
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5140
"""

import os
import csv
import paramiko

from scrapy.spiders import Spider
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


class PaddockSpares(Spider):
    name = 'bearmach-paddockspares'
    allowed_domains = ['paddockspares.com']
    start_urls = ['http://www.paddockspares.com/directory/currency/switch/currency/GBP']
    
    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "8PskJYFa"
        username = "bearmach"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        file_path = os.path.join(HERE, 'bearmach_products.csv')
        sftp.get('bearmach_feed.csv', file_path)

        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                allmakes_sku = row['Allmakes Part Number'].strip()
                britpart_sku = row['Britpart Part Number'].strip()

                brands = ['ALLMAKES', 'BRITPART']
                brands.append(row['Allmakes Brand'].upper().strip())
                brands.append(row['Britpart Brand'].upper().strip())

                if allmakes_sku == britpart_sku:
                    yield Request(
                        'http://www.paddockspares.com/catalogsearch/result/?q=%s' % allmakes_sku,
                        dont_filter=True,
                        callback=self.parse_search_results,
                        meta={'sku': allmakes_sku, 'brand': row['Allmakes Brand'].decode('latin-1'), 'brands': brands})
                else:
                    if allmakes_sku:
                        yield Request(
                            'http://www.paddockspares.com/catalogsearch/result/?q=%s' % allmakes_sku,
                            dont_filter=True,
                            callback=self.parse_search_results,
                            meta={'sku': allmakes_sku, 'brand': row['Allmakes Brand'].decode('latin-1'), 'brands': brands})

                    if britpart_sku:
                        yield Request(
                            'http://www.paddockspares.com/catalogsearch/result/?q=%s' % britpart_sku,
                            dont_filter=True,
                            callback=self.parse_search_results,
                            meta={'sku': britpart_sku, 'brand': row['Britpart Brand'].decode('latin-1'), 'brands': brands})
                
    def parse_search_results(self, response):
        products = response.css('.product-primary')
        if not products:
            for product in self.parse_product(response):
                yield product

        sku_searched = response.meta['sku']
        for product in products:
            if product.css('.sku::text').re('SKU: *(.+)')[0].strip().upper() == sku_searched.upper():
                yield Request(product.xpath('.//a/@href').extract_first(), self.parse_product, meta=response.meta)
                
    def parse_product(self, response):
        brand = response.meta['brand']
        brands = response.meta['brands']

        loader = ProductLoader(Product(), response=response)

        sku_searched = response.meta['sku']
        sku = response.css('.part-number strong::text').extract_first()
        if not sku or sku.strip().upper() != sku_searched:
            return

        product_brand = response.xpath('//tr[th[contains(text(), "Brand")]]/td[contains(@class, "data")]/text()').extract()[0]
        if product_brand.upper().strip() not in brands:
            return

        loader.add_value('identifier', sku)
        loader.add_value('url', response.url)
        loader.add_css('name', '.product-name .h1::text')
        loader.add_xpath('price', '//span[contains(@id, "price-excluding-tax")]/text()')
        loader.add_value('sku', sku)
        category = response.css('.breadcrumbs a::text').extract()[1:]
        loader.add_value('category', category)
        loader.add_css('image_url', 'img#image-main::attr(src)')
        loader.add_value('brand', brand)
        if response.css('.availability .out-of-stock'):
            loader.add_value('stock', 0)      
        item = loader.load_item()
        if item['price'] < 50:
            item['shipping_cost'] = 5
        yield item


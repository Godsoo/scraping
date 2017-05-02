# -*- coding: utf-8 -*-
"""
Account: Blivakker
Name: blivakker-blivakker.no
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4602-blivakker-|-client-site/details?tab=attachments
Original developer: Franco Almonacid <fmacr85@gmail.com>
"""


import re
import os
import csv
import json

from scrapy import Spider, FormRequest, Request
from product_spiders.items import (
    ProductLoaderWithNameStrip as ProductLoader,
    Product,
)

from product_spiders.utils import extract_price
from blivakkeritems import BlivakkerMeta
from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class BlivakkerSpider(Spider):
    name = 'blivakker-blivakker.no'
    allowed_domains = ['blivakker.no']

    filename = os.path.join(HERE, 'blivakker_products.csv')
    start_urls = ('file://' + filename,)


    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            yield Request(response.urljoin(row['ProductURL']), callback=self.parse_product, meta={'row': row})
       
    def parse_product(self, response):

        row = response.meta['row']

        name = response.xpath('//h1[@itemprop="name"]/text()').extract()[0]
        identifier = row['ProductNr']
        sales_price = ''.join(response.xpath('//div[@id="normal-product"]//span[@class="price-final"]/text()').extract()[0].split())
        list_price = response.xpath('//div[@id="normal-product"]//*[@id="is-on-sale-price"][@style!="display: none;"]/text()').extract_first()
        if list_price:
            price = list_price.replace(' ', '')
        else:
            price = sales_price
            sales_price = 0
            
        product_image = response.xpath('//img[@id="product-large-url"]/@src').extract()

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        loader.add_value('price', extract_price(price))

        if product_image:
            loader.add_value('image_url', product_image[0])
        loader.add_value('brand', row['Brand'].decode('ISO-8859-1'))
        loader.add_value('category', row['ReportCategoryName'].decode('ISO-8859-1'))

        item = loader.load_item()
        metadata = BlivakkerMeta()
        sku = row['EANNumber']
        metadata['sku'] = sku if sku else ''
        metadata['cost_price'] = row['ProductCostPriceExVat']
        if sales_price:
            metadata['SalesPrice'] = extract_price(sales_price)

        item['metadata'] = metadata

        yield item


# -*- coding: utf-8 -*-
"""
Account: Guitar Guitar
Name: guitar_guitar-guitarguitar.co.uk
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4595-guitar-guitar-|-client-spider/details#
Original developer: Franco Almonacid <fmacr85@gmail.com>
"""


import re
import os
import csv
import json
import xlrd

from scrapy import Spider, FormRequest, Request
from product_spiders.items import (
    ProductLoaderWithNameStrip as ProductLoader,
    Product,
)

from product_spiders.utils import extract_price
from guitarguitaritems import GuitarGuitarMeta

from cStringIO import StringIO

from product_spiders.base_spiders.primary_spider import PrimarySpider


HERE = os.path.abspath(os.path.dirname(__file__))


class GuitarGuitar(PrimarySpider):
    name = 'guitar_guitar-guitarguitar.co.uk'
    allowed_domains = ['guitarguitar.co.uk']

    filename = os.path.join(HERE, 'guitarguitar_products.csv')
    start_urls = ('file://' + filename,)

    csv_file = 'guitarguitar.co.uk_products.csv'

    def parse(self, response):
        tge_file = os.path.join(HERE, 'SKUstobeReplaced14-09-162.xlsx')
        wb = xlrd.open_workbook(tge_file)

        sh = wb.sheet_by_index(0)
        skus_to_ignore = []
        for rownum in xrange(sh.nrows):
            if rownum < 2:
                continue

            row = sh.row(rownum)
            if row[0].value:
                skus_to_ignore.append(str(int(row[0].value)))

        search_url = "http://www.guitarguitar.co.uk/search.asp?brandname=&search=%s&x=0&y=0"
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            if row['SKU'] not in skus_to_ignore:
                yield Request(search_url % row['SKU'], callback=self.parse_search, meta={'row': row})

        sh = wb.sheet_by_index(1)
        row = sh.row(rownum)
        for rownum in xrange(sh.nrows):
            if rownum < 2:
                continue

            row = sh.row(rownum)
            if row[0].value:
                sku = str(int(row[0].value))
                yield Request(search_url % sku, callback=self.parse_search, meta={'row': {'SKU': sku,
                                                                                          'BRAND': row[1],
                                                                                          'PRODUCT CODE': ''}})

    def parse_search(self, response):
        row = response.meta['row']
        products = response.xpath('//div[@class="list_item"]/a/@href').extract()
        found = False
        for product in products:
            if row['SKU'] in product:
                found = True
                yield Request(response.urljoin(product), callback=self.parse_product, meta=response.meta)
                break
        if not found and row.get('URL', None):
            yield Request(row['URL'], callback=self.parse_product, meta=response.meta)
        
    def parse_product(self, response):

        row = response.meta['row']

        name = response.xpath('//h1/text()').extract()[0]
        identifier = row['SKU']
        price = response.xpath('//strong[@itemprop="price"]/text()').extract()
        price = extract_price(price[0]) if price else 0
        out_of_stock = response.xpath('//div[@class="vgg-availability"]/div[@class="nostock"]')
        product_image = response.xpath('//div[contains(@class, "vgg-image-center")]/a/img/@src').extract()
        categories = response.xpath('//div[@id="breadcrumb"]/a/text()').extract()[:-1]

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        loader.add_value('price', price)
        if out_of_stock:
            loader.add_value('stock', 0)
        if product_image:
            loader.add_value('image_url', response.urljoin(product_image[0]))
        loader.add_value('brand', row['BRAND'])
        loader.add_value('category', categories)

        item = loader.load_item()
        metadata = GuitarGuitarMeta()
        metadata['mpn'] = row['PRODUCT CODE']
        item['metadata'] = metadata

        yield item


# -*- coding: utf-8 -*-
"""
Customer: HargrovesCycles
Website: http://www.hargrovescycles.co.uk
Crawling process: download spreadsheet from Google Docs using the download link and 
extract the urls in the file.
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4306

IMPORTANT! the spider should only extract the option with the same SKU as in the file.
"""

import os
import csv
import json
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

from scrapy.item import Item, Field

HERE = os.path.abspath(os.path.dirname(__file__))

class HargrovesCyclesMeta(Item):
    mpn = Field()


class HargrovesCyclesSpider(BaseSpider):
    name = 'hargrovescycles-hargrovescycles.co.uk'
    # Google doc spreadsheet download link
    start_urls = ('https://docs.google.com/spreadsheets/d/1BsVRktvtFG2M6Qmywa9RJ7VcqaUgePKIL1vR8E_ex1k/export?format=csv&id=1BsVRktvtFG2M6Qmywa9RJ7VcqaUgePKIL1vR8E_ex1k',)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            yield Request(row['url'], callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        row = response.meta['row']

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('identifier', row['our part no.'].lower())
        loader.add_value('sku', row['our part no.'])
        loader.add_value('url', response.url)
        brand = hxs.select('//img[@class="manufacturer_image"]/@title').extract()
        brand = brand[0].strip() if brand else ''
        loader.add_value('brand', brand)
        loader.add_value('category', brand)
        loader.add_xpath('image_url', '//div[@class="product-image"]//img/@src')
        loader.add_xpath('name', '//h1/text()')
        price = extract_price(''.join(''.join(hxs.select('//form//p[@class="special-price"]//span[@class="price"]/text()').extract()).split()))
        if not price:
            price = extract_price(''.join(''.join(hxs.select('//span[@class="regular-price"]//span[@class="price"]/text()').extract()).split()))
        loader.add_value('price', price)

        item = loader.load_item()

        metadata = HargrovesCyclesMeta()
        metadata['mpn'] =row['mpn']
        
        item['metadata'] = metadata

        option_found = False

        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            prices = {}

            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))
                        prices[product] = prices.get(product, 0) + extract_price(option['oldPrice'])
            
            for option_id, option_name in products.iteritems():
                # Check for the correct options according to the google doc spreadsheet
                if product_data['products'][option_id]['sku'].upper() == item['sku'].upper():
                    item['price'] = product_data['childProducts'][option_id]['finalPrice']
                    item['name'] += ' ' + option_name
                    stock = product_data['products'][option_id].get('saleable', False)
                    if not stock:
                        item['stock'] = 0
                    yield item
        else:
            out_of_stock = hxs.select('//div[contains(@class, "product-info")]//span[@class="stock"]/span[@class="outstock"]')
            if out_of_stock:
                item['stock'] = 0
            yield item

"""
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/3940-e-bedding---new-site---sleepypeople#/activity/ticket:
This spider searches for product codes in a flat file, pagination is not required because there's a limit=all parameter.
Each product's SKU is matched against all of the searched SKUs before extraction.
"""
import json
import re
import os
import csv
import urllib
from urlparse import urljoin as urljoin_rfc

from cStringIO import StringIO

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy import log
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price

from ebeddingitems import EbeddingMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class EBeddingArgosSpider(BaseSpider):
    name = 'ebedding-sleepypeople.com'
    allowed_domains = ['sleepypeople.com']

    filename = os.path.join(HERE, 'ebedding_products.csv')
    start_urls = ('file://' + filename,)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            if row['Product page URL']:
                yield Request(row['Product page URL'], dont_filter=True, callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        row = response.meta['row']

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('identifier', row['Unique product code'])
        loader.add_value('sku', row['Unique product code'])
        loader.add_value('url', response.url)
        loader.add_value('brand', row['Brand'])
        loader.add_value('category', row['Category'])
        loader.add_value('name', row['Product name'])

        image_url = response.xpath('//p[contains(@class, "product-image")]/a/@href').extract()
        image_url = image_url[0] if image_url else ''
        loader.add_value('image_url', image_url)

        price = response.xpath('//div[@class="add_to_cart"]//span[@class="regular-price"]//span/text()').extract()
        if not price:
            price = response.xpath('//div[@class="add_to_cart"]//p[@class="special-price"]//span[@class="price"]/text()').extract()
        loader.add_value('price', price[0])

        out_of_stock = response.xpath('//p[@class="availability out-of-stock"]')
        if out_of_stock:
            loader.add_value('stock', 0)

        option_text = row['Product name'].split(' - ')[-1]

        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            sku_data = re.search('var care_attribs = (.*);', response.body).group(1)
            sku_data = json.loads(sku_data)

            products = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product_id in option['products']:
                        products[product_id] = ' - '.join((products.get(product_id, ''), option['label']))

            for identifier, option_name in products.iteritems():
                if sku_data[identifier]['attrib_sku']['value'] == row['Unique product code']:
                    loader.replace_value('price', product_data['childProducts'][identifier]['finalPrice'])
                    stock = product_data['stockInfo'][identifier]['stockQty']
                    if not stock:
                        loader.replace_value('stock', 0)
                    break

        item = loader.load_item()
        
        metadata = EbeddingMeta()
        metadata['cost_price'] = row['Cost price']
        metadata['ean'] = row['EAN']

        item['metadata'] = metadata

        yield item
         

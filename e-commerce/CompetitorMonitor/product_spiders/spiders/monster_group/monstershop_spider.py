import os
import re
import csv
import json
from copy import deepcopy
from scrapy import Spider

from scrapy.http import Request

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class MonsterShopSpider(Spider):
    name = 'monster_group-monstershop.co.uk'
    start_urls = ['https://www.monstershop.co.uk']

    def start_requests(self):
        filename = os.path.join(HERE, 'monstershop_products.csv')
        with open(filename) as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield Request(row['Product URL'], meta={'row': row})

    def parse(self, response):

        row = response.meta['row']

        name = response.xpath('//h1[contains(@class, "c-product__title")]/text()').extract()[0].strip()
        price = response.xpath('//span[@itemprop="price"]/text()').extract()[0].strip()
        brand = response.xpath('//tr[th[contains(text(), "Manufacturer")]]/td/text()').extract()
        brand = brand[0].strip() if brand else ''
        categories = response.xpath('//section[@class="c-breadcrumbs"]//a/text()').extract()[1:]

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('identifier', row['Unique Code'].lower())
        loader.add_value('sku', row['Unique Code'])
        loader.add_value('brand', row['Product Brand/Category'])
        loader.add_value('category', row['Product Brand/Category'])
        loader.add_value('name', row['Product Name'])
        loader.add_value('url', response.url)
        loader.add_value('image_url', row['Product Image URL'])
        loader.add_value('price', price)
        item = loader.load_item()
 
        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))

            for identifier, option_name in products.iteritems():
                option_item = deepcopy(item)
                option_item['identifier'] += '-' + identifier
                option_item['name'] = name + option_name
                yield option_item
        else:
            yield item

# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url

import json
import os
import re
import csv

from cStringIO import StringIO

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

from scrapy.item import Item, Field


class SpecMeta(Item):
    lens_type = Field()


class SpecSavers(BaseSpider):
    name = 'specsavers_au-specsavers.com.au'
    allowed_domains = ['specsavers.com.au']

    filename = os.path.join(HERE, 'specsavers.csv')
    start_urls = ('file://' + filename,)

    url_field = 'AU'
    price_field = '$au'
    
    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            url = row[self.url_field]
            if url:
                yield Request(url, meta={'row': row}, callback=self.parse_product)
            else:
                identifier = row.get('PLU', None)
                if identifier:
                    brand = row['Vendor'].decode('utf-8')
                    name = row['Product Title'].decode('utf-8') + ' ' + row['Lens Type'].decode('utf-8')

                    loader = ProductLoader(item=Product(), response=response)
                    loader.add_value('name', name)
                    loader.add_value('identifier', identifier)
                    loader.add_value('sku', identifier)
                    loader.add_value('url', '')
                    loader.add_value('brand', brand)
                    loader.add_value('stock', 0)

                    loader.add_value('price', row[self.price_field])
                    p = loader.load_item()

                    meta = SpecMeta()
                    meta['lens_type'] = row['Lens Type'].decode('utf-8')
                    p['metadata'] = meta
                    yield p
                

    def parse_product(self, response):
        base_url = get_base_url(response)

        row = response.meta['row']

        brand = row['Vendor'].decode('utf-8')
        name = row['Product Title'].decode('utf-8') + ' ' + row['Lens Type'].decode('utf-8')
       
        product = re.findall('"products":(.*)}}}', response.body)
        if product:
            product = json.loads(product[0])[0]

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('identifier', product['id'])
            loader.add_value('sku', product['id'])
            loader.add_value('url', response.url)
            loader.add_value('brand', brand)
            loader.add_value('category', product['category'])
            image_url = response.xpath('//img[contains(@class, "img-responsive")]/@src').extract()
            if image_url:
                loader.add_value('image_url', image_url)
            loader.add_value('price', product['price'])

            meta = SpecMeta()
            meta['lens_type'] = row['Lens Type'].decode('utf-8')
            p = loader.load_item()
            p['metadata'] = meta
            yield p
        else:
            identifier = row.get('PLU', None)
            if identifier:
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('name', name)
                loader.add_value('identifier', identifier)
                loader.add_value('sku', identifier)
                loader.add_value('url', '')
                loader.add_value('brand', brand)
                loader.add_value('stock', 0)
                image_url = response.xpath('//div[@class="prod-img"]/img/@src').extract()
                if image_url:
                    image_url = 'http://' + image_url[0] if 'http' not in image_url[0] else image_url[0]
                loader.add_value('image_url', image_url)

                price = response.xpath('//div[contains(@class, "product all-inclusive-only")]//text()').re(u'£(\d+.\d+)')
                if price:
                    price = price[0]
                else:
                    price = row[self.price_field]
                loader.add_value('price', price)
                p = loader.load_item()

                meta = SpecMeta()
                meta['lens_type'] = row['Lens Type'].decode('utf-8')
                p['metadata'] = meta
                yield p



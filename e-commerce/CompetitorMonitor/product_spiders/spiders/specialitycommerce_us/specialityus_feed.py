# -*- coding: utf-8 -*-
"""
Customer: Speciality Commerce US
Crawling process: reads client feed

IMPORTANT! this spider copies it results to be used by the amazon spider 
in this account.

"""

import os
import csv
import shutil
import StringIO

from scrapy.spider import BaseSpider
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy import log

from scrapy.item import Item, Field

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class SpecialityMeta(Item):
    cost_price = Field()
    msrp = Field()
    standard_price = Field()


class SpecialityUSSpider(BaseSpider):
    name = 'specialitycommerceus-feed'
    allowed_domains = ['74.8.144.60']
    start_urls = ('http://74.8.144.60/IntelligentEye/especiallyyours_IntelligentEye.csv',
                  'http://74.8.144.60/IntelligentEye/wig_IntelligentEye.csv')

    def ___init__(self, *a, **kw):
        super(SpecialityUSSpider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def closed(self, reason):
        try:
            shutil.copy('data/%s_products.csv' % self.crawl_id, os.path.join(HERE, 'specialitycommerceus_products.csv'))
        except IOError:
            shutil.copy('data/%s_products.csv' % self.prev_crawl_id, os.path.join(HERE, 'specialitycommerceus_products.csv'))
        log.msg("CSV is copied")


    def parse(self, response):
        reader = csv.DictReader(StringIO.StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            identifier = row.get('Unique Product Code')
            if not identifier:
                self.log('ERROR product without identifier')
                continue
            loader.add_value('identifier', identifier.strip())
            loader.add_value('sku', identifier.strip())
            loader.add_value('brand',  unicode(row.get('Brand', ''), errors='ignore'))
            loader.add_value('category',  unicode(row.get('Category', ''), errors='ignore'))
            product_name = '{} {}'.format(row.get('Product Name', ''), row.get('Vendor Colour Code', ''))
            loader.add_value('name',  unicode(product_name, errors='ignore'))
            loader.add_value('price', row.get('Price', ''))
            loader.add_value('url', row.get('Product Page URL',''))
            loader.add_value('image_url', row.get('Image URL', ''))
            if row.get('Stock Availability', '') != 'In Stock':
                loader.add_value('stock', 0)
            metadata = SpecialityMeta()
            product = loader.load_item()
            metadata['cost_price'] = row.get('Cost Price', '')
            metadata['msrp'] = row.get('MAP', '')
            metadata['standard_price'] = row.get('Standard Price', '')
            product['metadata'] = metadata

            yield product

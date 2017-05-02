# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import os
import csv

from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.loader.processor import MapCompose, Join
from scrapy.utils.markup import remove_entities
from items import Product
from base_spiders.target.targetspider import BaseTargetSpider, TargetProductLoader
from householditems import ProductLoader as HouseholdProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class UnifiedBrand(object):
    replacements = [
        ('Babycakes', 'Baby Cakes'),
        ('Black &Decker', 'Black & Decker'),
        ('KitchenAid', 'Kitchen Aid'),
        ('Nutribullet', 'Nutri Bullet'),
        ('Proctor-Silex', 'Proctor Silex'),
        ('Tefal', 'T-Fal'),
        ('ninja', 'Ninja')]

    def __call__(self, values):
        j = Join()
        brand = j(values)
        for b, r in self.replacements:
            b_tmp = brand.replace(' ', '').replace('-', '').lower()
            r_tmp = r.replace(' ', '').replace('-', '').lower()
            if b_tmp == r_tmp or b.lower() == brand.lower():
                return r
        return brand


class HouseholdTargetProductLoader(HouseholdProductLoader, TargetProductLoader):
    brand_in = MapCompose(unicode, remove_entities)
    brand_out = UnifiedBrand()


class TargetSpider(BaseTargetSpider):
    name = 'householdessentials-target.com'
    start_urls = ('http://www.target.com/bp/keurig',)

    category_type = 'ordered'

    ProductLoaderCls = HouseholdTargetProductLoader

    def __init__(self, *args, **kwargs):
        super(TargetSpider, self).__init__(*args, **kwargs)

        self.urls = []

        with open(os.path.join(HERE, 'householdessentials_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row['Target TCIN']
                if code != '#N/A':
                    url = 'http://tws.target.com/searchservice/item/search_results/v2/by_keyword?search_term=%s&' + \
                          'alt=json&pageCount=900000&response_group=Items&zone=mobile&offset=0'
                    search = {'url': url % code,
                              'brand': row.get('Brand', ''),
                              'sku': row['Item Number']}
                    self.urls.append(search)

    def start_requests(self):
        for url in self.urls:
            yield Request(url['url'], meta={'brand': url['brand'], 'sku': url['sku']})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        out_stock = bool(hxs.select('//div[@class="shipping"]//*[contains(text(), "not available")]'))

        for obj in super(TargetSpider, self).parse_product(response):
            if out_stock:
                if isinstance(obj, Request):
                    obj.meta['product']['stock'] = 0
                elif isinstance(obj, Product):
                    obj['stock'] = 0
            yield obj

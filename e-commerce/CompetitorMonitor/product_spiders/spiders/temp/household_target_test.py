# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import os
import csv

from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.loader.processor import MapCompose, Join
from scrapy.utils.markup import remove_entities

from base_spiders.target.targetspider import BaseTargetSpider, TargetProductLoader
from product_spiders.spiders.household_essentials.householditems import ProductLoader as HouseholdProductLoader

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


class TargetTestSpider(BaseTargetSpider):
    name = 'household-target.com-test'
    start_urls = ('http://www.target.com/bp/keurig',)

    category_type = 'ordered'

    ProductLoaderCls = HouseholdTargetProductLoader

    def __init__(self, *args, **kwargs):
        super(TargetTestSpider, self).__init__(*args, **kwargs)

        self.urls = []

        with open(os.path.join(HERE, 'householdessentials_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row['Target TCIN']
                if code != '#N/A':
                    url = {'url':'http://www.target.com/s?searchTerm=%s' % code,
                           'brand': row.get('Brand', ''),
                           'sku': row['Item Number']}
                    self.urls.append(url)

    def start_requests(self):
        for url in self.urls:
            yield Request(url['url'], meta={'brand': url['brand'], 'sku': url['sku']})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        product_urls = hxs.select('//div[@class="tileInfo"]/a/@href').extract()
        for url in product_urls:
            yield Request(url, callback=self.parse_product, meta=response.meta)

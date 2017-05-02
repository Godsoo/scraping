# -*- coding: utf-8 -*-
import os.path

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class ScrewfixSpider_C(SecondaryBaseSpider):
    name = 'arco-c-screwfix.com'
    allowed_domains = ['screwfix.com']

    csv_file = 'arco_a/screwfix_products.csv'

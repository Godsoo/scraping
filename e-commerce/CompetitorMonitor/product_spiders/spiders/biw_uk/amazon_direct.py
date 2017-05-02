# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import os.path

from product_spiders.spiders.bi_worldwide_usa.amazon_direct import BIWAmazonDirectSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class BIWAmazonDirectUKSpider(BIWAmazonDirectSpider):
    name = "biw_uk_amazon_direct"
    domain = "amazon.co.uk"

    only_buybox = True
    amazon_direct = False

    file_start_with = 'BI UK File'
    file_extension = 'csv'
    root = HERE

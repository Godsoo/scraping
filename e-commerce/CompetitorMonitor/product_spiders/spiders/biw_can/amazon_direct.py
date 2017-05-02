# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import os.path

from product_spiders.spiders.bi_worldwide_usa.amazon_direct import BIWAmazonDirectSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class BIWAmazonDirectCanSpider(BIWAmazonDirectSpider):
    name = "biw_can_amazon_direct"
    domain = "amazon.ca"

    file_start_with = 'BI CAN File'
    root = HERE
    extract_warranty = False
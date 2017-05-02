# -*- coding: utf-8 -*-

from cdiscount_base_spider import CDiscountBaseSpider, PROXIES

class CDiscountTestSpider2(CDiscountBaseSpider):
    name = 'cdiscount_test_spider_2'
    proxy = PROXIES[2]
# -*- coding: utf-8 -*-

from cdiscount_base_spider import CDiscountBaseSpider, PROXIES

class CDiscountTestSpider1(CDiscountBaseSpider):
    name = 'cdiscount_test_spider_1'
    proxy = PROXIES[1]
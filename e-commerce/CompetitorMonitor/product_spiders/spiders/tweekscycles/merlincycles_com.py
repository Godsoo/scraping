# -*- coding: utf-8 -*-

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class MerlinCyclesSpider(SecondaryBaseSpider):
    name = 'tweekscycles-merlincycles.com'
    allowed_domains = ['merlincycles.com']
    start_urls = ('http://www.merlincycles.com/',)

    csv_file = 'pedalpedal/merlincycles.com_crawl.csv'

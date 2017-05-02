# -*- coding: utf-8 -*-

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class MerlinCyclesSpider(SecondaryBaseSpider):
    name = u'ribblecycles-merlincycles.com'
    allowed_domains = ['merlincycles.com']

    start_urls = ('http://www.merlincycles.com/',)

    csv_file = 'sigmasport/merlincycles.com_crawl.csv'

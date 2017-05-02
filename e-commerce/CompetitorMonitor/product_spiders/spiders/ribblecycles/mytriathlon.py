# -*- coding: utf-8 -*-

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class MyTriathlonSpider(SecondaryBaseSpider):
    name = 'ribblecycles-mytriathlon.co.uk'
    allowed_domains = ['mytriathlon.co.uk', 'competitormonitor.com']
    csv_file = 'sigmasport/mytriathlon.co.uk_crawl.csv'
    start_urls = ['http://mytriathlon.co.uk']

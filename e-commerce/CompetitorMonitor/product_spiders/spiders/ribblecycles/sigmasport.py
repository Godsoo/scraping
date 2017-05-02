# -*- coding: utf-8 -*-

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class SigmaSportSpider(SecondaryBaseSpider):
    name = 'ribblecycles-sigmasport.co.uk'
    allowed_domains = ['sigmasport.co.uk', 'competitormonitor.com']
    csv_file = 'sigmasport/sigmasport.co.uk_crawl.csv'
    start_urls = ('http://www.sigmasport.co.uk',)

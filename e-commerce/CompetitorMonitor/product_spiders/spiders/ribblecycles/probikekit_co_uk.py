# -*- coding: utf-8 -*-

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class ProbikekitSpider(SecondaryBaseSpider):
    name = u'ribblecycles-probikekit.co.uk'
    allowed_domains = ['www.probikekit.co.uk']

    start_urls = ['http://www.probikekit.co.uk']

    csv_file = 'sigmasport/probikekit.co.uk_crawl.csv'

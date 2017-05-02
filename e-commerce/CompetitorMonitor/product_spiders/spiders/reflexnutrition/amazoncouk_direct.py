# -*- coding: utf-8 -*-

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class AmazonSpider(SecondaryBaseSpider):

    name = 'reflexnutrition-amazon.co.uk'
    allowed_domains = ['amazon.co.uk']
    start_urls = ['http://www.amazon.co.uk']

    csv_file = 'usn/usn_amazoncouk_crawl.csv'

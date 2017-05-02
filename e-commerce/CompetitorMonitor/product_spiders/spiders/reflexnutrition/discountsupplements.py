# -*- coding: utf-8 -*-

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class DiscountSupplementsSpider(SecondaryBaseSpider):

    name = 'reflexnutrition-discount-supplements.co.uk'
    allowed_domains = ['discount-supplements.co.uk']
    start_urls = ['http://www.discount-supplements.co.uk']

    csv_file = 'usn/discount-supplements.co.uk_crawl.csv'

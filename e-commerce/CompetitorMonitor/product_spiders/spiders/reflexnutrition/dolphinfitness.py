# -*- coding: utf-8 -*-

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class DolphinFitnessSpider(SecondaryBaseSpider):
    name = 'reflexnutrition-dolphinfitness.co.uk'
    allowed_domains = ['dolphinfitness.co.uk']
    start_urls = ['http://www.dolphinfitness.co.uk']

    csv_file = 'usn/dolphinfitness.co.uk_crawl.csv'

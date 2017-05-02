# -*- coding: utf-8 -*-

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class BodyBuildingSpider(SecondaryBaseSpider):

    name = 'reflexnutrition-bodybuilding.com'
    allowed_domains = ['bodybuilding.com']
    start_urls = ['http://uk.bodybuilding.com']

    csv_file = 'usn/bodybuilding.com_crawl.csv'

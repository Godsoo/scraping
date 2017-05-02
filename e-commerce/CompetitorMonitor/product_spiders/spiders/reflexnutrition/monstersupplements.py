# -*- coding: utf-8 -*-

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class MonsterSupplementsSpider(SecondaryBaseSpider):

    name = 'reflexnutrition-monstersupplements.com'
    allowed_domains = ['monstersupplements.com']
    start_urls = ['http://monstersupplements.com']

    csv_file = 'usn/monstersupplements.com_crawl.csv'

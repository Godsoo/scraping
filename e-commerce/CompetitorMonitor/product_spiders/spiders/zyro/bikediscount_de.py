# -*- coding: utf-8 -*-

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class BikeDiscountDeSpider(SecondaryBaseSpider):

    name = 'zyro-bike-discount.de'
    allowed_domains = ['bike-discount.de']
    start_urls = ['http://www.bike-discount.de/en/']

    csv_file = 'pedalpedal/bike-discount.de_crawl.csv'

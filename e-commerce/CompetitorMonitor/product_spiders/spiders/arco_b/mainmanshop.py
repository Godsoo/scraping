# -*- coding: utf-8 -*-

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class MainmanshopSpider(SecondaryBaseSpider):
    name = 'arco_b-mainmanshop.co.uk'
    allowed_domains = ['mainmanshop.co.uk']
    start_urls = ['http://www.mainmanshop.co.uk/']

    csv_file = 'arco_a/mainmanshop_crawl.csv'

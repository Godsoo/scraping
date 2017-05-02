# -*- coding: utf-8 -*-
__author__ = 'juraseg'

from product_spiders.base_spiders.primary_spider import PrimarySpider

from product_spiders.base_spiders.unified_marketplace_spider import UnifiedMarketplaceSpider


class AmazonCoUkMarketplaceSpider(UnifiedMarketplaceSpider, PrimarySpider):
    name = "usn_amazoncouk_marketplace"
    domain = "amazon.co.uk"
    market_type = 'marketplace'
    data_filename = 'usn_amazoncouk'

    csv_file = 'usn_amazoncouk_crawl.csv'

    start_urls = ['http://amazon.co.uk']

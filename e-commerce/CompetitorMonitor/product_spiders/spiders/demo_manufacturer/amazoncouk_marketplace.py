# -*- coding: utf-8 -*-

from product_spiders.base_spiders.unified_marketplace_spider import UnifiedMarketplaceSpider


class AmazonCoUkMarketplaceSpider(UnifiedMarketplaceSpider):
    name = "demo_manufacturer-amazon.co.uk_marketplace"
    domain = "amazon.co.uk"
    market_type = 'marketplace'
    data_filename = 'demo_manufacturer_amazoncouk'

    start_urls = ['http://amazon.co.uk']

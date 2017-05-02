# -*- coding: utf-8 -*-

import csv
import os.path

from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector


from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider
from product_spiders.base_spiders.amazonspider2.scraper import AmazonScraperProductDetailsException
from product_spiders.base_spiders.unified_marketplace_spider import UnifiedMarketplaceSpider

HERE = os.path.abspath(os.path.dirname(__file__))

class JerseyElectricityAmazonBuyBox(UnifiedMarketplaceSpider):
    name = "qatesting-amazon-unified-marketplace-test"
    allowed_domains = ["amazon.co.uk"]
    market_type = 'marketplace'
    data_filename = 'qatesting-jerseyamazon'
    start_urls = ['http://amazon.co.uk']
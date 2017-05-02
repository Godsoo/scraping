# -*- coding: utf-8 -*-
import csv
import os

from scrapy import log
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider
from brands import BrandSelector

HERE = os.path.abspath(os.path.dirname(__file__))


class AmazonSpiderDirect(SecondaryBaseSpider):
    name = 'toymonitor-main-amazon.co.uk'
    csv_file = 'toymonitor/toymonitor_amazon_crawl.csv'

    allowed_domains = ('amazon.co.uk',)
    start_urls = ('http://amazon.co.uk',)
    errors = []
    brand_selector = BrandSelector(errors)
    #field_modifiers = {'brand': brand_selector.get_brand}

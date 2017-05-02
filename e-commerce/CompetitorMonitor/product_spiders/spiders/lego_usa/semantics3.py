import os
import csv
import re
import json
import urlparse
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

class Semantics3AmazonSpider(BaseSpider):
    name = 'legousa-semantics3-amazon.com'
    allowed_domains = ['semantics3.com']

    def start_requests(self):
        pass

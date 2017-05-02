import os
import csv
import cStringIO

import re
import json
import urlparse
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

from phantomjs import PhantomJS
import time

from scrapy import log


class NisbetsSpider(SecondaryBaseSpider):
    name = 'caterkwik-nisbets.co.uk'
    allowed_domains = ['nisbets.co.uk']
    start_urls = ('http://www.nisbets.co.uk/Homepage.action',)

    csv_file = 'cscatering/nisbets_products.csv'
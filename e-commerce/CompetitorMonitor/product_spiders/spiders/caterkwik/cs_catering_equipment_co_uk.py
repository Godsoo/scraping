import os
import csv
import cStringIO

import re
import json
import urlparse
from scrapy.spider import BaseSpider
from scrapy.selector import XmlXPathSelector
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.item import Item, Field

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

from scrapy import log

class CSCateringSpider(SecondaryBaseSpider):
    name = 'caterkwik-cs-catering-equipment.co.uk'
    allowed_domains = ['cs-catering-equipment.co.uk']
    start_urls = ('http://www.cs-catering-equipment.co.uk/',)

    csv_file = 'cscatering/cscatering_products.csv'
    json_file = 'cscatering/cscatering_metadata.json'

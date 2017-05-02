import re
import json
import urlparse
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price, fix_spaces
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

from scrapy import log

class CaterKwikSpider(SecondaryBaseSpider):
    name = 'caterkwik-caterkwik.co.uk'
    allowed_domains = ['caterkwik.co.uk']
    start_urls = ('http://www.caterkwik.co.uk/',)

    csv_file = 'cscatering/carterkwik_products.csv'
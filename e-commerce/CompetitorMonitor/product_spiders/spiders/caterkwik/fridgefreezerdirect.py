import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

from copy import deepcopy
# import copy
# import itertools


class FridgeFreezerDirectSpider(SecondaryBaseSpider):
    name = 'caterkwik-fridgefreezerdirect.co.uk'
    allowed_domains = ['fridgefreezerdirect.co.uk']
    start_urls = ('https://www.fridgefreezerdirect.co.uk',)

    csv_file = 'cscatering/fridgefreezerdirect_products.csv'

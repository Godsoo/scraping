# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector, XmlXPathSelector
from scrapy.contrib.loader import ItemLoader
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
import re, time

class TredzSpider(SecondaryBaseSpider):

    name = "zyro-tredz.co.uk"
    start_urls = ["http://www.tredz.co.uk"]
    allowed_domains = ['tredz.co.uk']

    csv_file = 'pedalpedal/tredz.co.uk_products.csv'    
import logging
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price_eu
from basespider import BaseRosarioSpider


class maxclima80_spider(BaseRosarioSpider):
    name = 'maxclima80.ebay'
    allowed_domains = ['www.ebay.it', 'stores.ebay.it', 'ebay.it', 'ebay.com']
    start_urls = ('http://stores.ebay.it/vimaclima',)

    def __init__(self, *a, **kw):
        super(maxclima80_spider, self).__init__(*a, **kw)

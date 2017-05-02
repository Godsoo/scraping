import logging

from scrapy import log, signals
from scrapy.http import Request, HtmlResponse
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price_eu
from basespider import BaseRosarioSpider

class TECLIMA_spider(BaseRosarioSpider):
    name = 'TEKCLIMA.ebay'
    start_urls = ('http://stores.ebay.it/TEKCLIMA',)

    def __init__(self, *a, **kw):
        super(TECLIMA_spider, self).__init__(*a, **kw)

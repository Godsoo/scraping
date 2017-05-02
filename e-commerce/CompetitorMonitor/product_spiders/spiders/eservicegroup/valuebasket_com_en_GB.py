import os
import re
import shutil
import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from decimal import Decimal
from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.contrib.loader.processor import TakeFirst, Compose, Join

HERE = os.path.abspath(os.path.dirname(__file__))

def onlyDecimal(a):
    return re.sub(r'[^0-9.]', '', a)

class ValueBasketComEnGBSpider(BaseSpider):
    name = 'valuebasket.com_en_GB'
    allowed_domains = ['www.valuebasket.com', 'valuebasket.com']
    start_urls = ['http://www.valuebasket.com/en_GB/']

    def __init__(self, *args, **kwgs):
        super(ValueBasketComEnGBSpider, self).__init__(*args, **kwgs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def spider_closed(self, spider):
        if spider.name == self.name:
            shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(os.path.dirname(HERE),
                        'procamerashop/valuebasket.csv'))
            self.log('CSV is copied')

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        xpath_str = '//div[@id="footer"]//ul/li/p/a/@href'
        pages = hxs.select(xpath_str).extract()

        for page in pages:
            yield Request(urljoin_rfc(base_url, page),
                          callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        xpath_str = '//a[@class="prd-image"]/@href'
        pages = hxs.select(xpath_str).extract()

        for page in pages:
            yield Request(urljoin_rfc(base_url, page),
                          callback=self.parse_product)

        # parse next page
        xpath_str = '//li[@class="next"]/a/@href'
        pages = hxs.select(xpath_str).extract()

        if pages and len(pages) > 0:
            yield Request(urljoin_rfc(base_url, pages[0]),
                          callback=self.parse_category)


    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(response=response, item=Product())
        """
        - product code (SKU)
        - price
        - product name
        - product URL
        - category
        - brand (if possible)
        - product image URL
        - shipping cost (if possible)
        """
        loader.add_xpath('price', '//div[@class="order"]/ins/var/text()', TakeFirst(), Compose(onlyDecimal))
        loader.add_xpath('identifier', '//link[@rel="canonical"]/@href', re='mainproduct/view/(.*)')
        loader.add_xpath('sku', '//link[@rel="canonical"]/@href', re='mainproduct/view/(.*)')
        loader.add_value('url', urljoin_rfc(base_url, response.url))
        loader.add_xpath('name', '//div[@class="product-additional"]/h1/text()')
        loader.add_xpath('image_url', '//div[@class="graphics"]//img/@src')
        loader.add_xpath('category', '//div[@id="breadcrumbs"]//a/span[@itemprop="title"]/text()', Compose(lambda v: v[1:]), Join(' > '))

        cost = hxs.select('//div[@class="order"]/div/var/text()').extract()
        if cost and len(cost) > 0 and cost[0] == 'Free shipping':
            loader.add_value('shipping_cost', Decimal('0.00'))

        yield loader.load_item()

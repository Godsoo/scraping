import csv
import os
import shutil
import StringIO
from datetime import datetime
from decimal import Decimal
from math import ceil

from scrapy.spider import BaseSpider
from scrapy import signals
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.items import Product, \
    ProductLoaderWithNameStrip as ProductLoader

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class ScrewfixSpider(BaseSpider):
    name = 'arco-screwfix.com'
    allowed_domains = ['screwfix.com', 'competitormonitor.com']

    def __init__(self, *args, **kwargs):
        super(ScrewfixSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        self.prods_count = 0

    def start_requests(self):
        if self.full_run_required():
            start_req = self._start_requests_full()
            log.msg('Full run')
        else:
            start_req = self._start_requests_simple()
            log.msg('Simple run')

        for req in start_req:
            yield req

    def spider_closed(self, spider):
        if spider.name == self.name:
            shutil.copy('data/%s_products.csv' % spider.crawl_id,
                        os.path.join(HERE, 'screwfix_products.csv'))

    def _start_requests_full(self):
        yield Request('http://www.screwfix.com/', callback=self.parse_full)

    def _start_requests_simple(self):
        yield Request('http://competitormonitor.com/login.html'
                      '?action=get_products_api&website_id=484723&matched=1',
                      callback=self.parse_simple)

    def full_run_required(self):
        if not os.path.exists(os.path.join(HERE, 'screwfix_products.csv')):
            return True

        # run full only on Mondays
        return datetime.now().weekday() == 0

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        cats = hxs.select('//ul[@id="main-nav"]//a/@href').extract()
        for cat in cats:
            yield Request(urljoin_rfc(get_base_url(response), cat),
                          callback=self.parse_subcats_full)

    def parse_subcats_full(self, response):
        hxs = HtmlXPathSelector(response)

        subcats = hxs.select('//a[@class="range_links"]/@href').extract()

        subcats.extend(hxs.select('//a[@forsubcatid]/@href').extract())
        subcats.extend(hxs.select('//a[@class="page-link"]/@href').extract())

        for cat in subcats:
            yield Request(urljoin_rfc(get_base_url(response), cat),
                          callback=self.parse_subcats_full)

        for product in self.parse_products(hxs):
            yield product

    def parse_products(self, hxs):
        products = hxs.select('//div[@class="product-info"]/..')
        if not products:
            products = hxs.select('//div[@class="pad"]')

        for product in products:
            self.prods_count += 1

            price = product.select('.//em[starts-with(@id, "product_list_price")]/text()').re(r'[\d.,]+')[0].replace(',', '')
            price = ceil(Decimal(price) / Decimal('1.2') * 100) / 100

            loader = ProductLoader(selector=product, item=Product())
            loader.add_xpath('name', './/a[starts-with(@id, "product_description")]/text()')
            loader.add_xpath('url', './/a[starts-with(@id, "product_description")]/@href')
            loader.add_value('price', price)
            loader.add_xpath('identifier', './/span/@quotenumberproductid')

            yield loader.load_item()

    def parse_simple(self, response):
        f = StringIO.StringIO(response.body)
        hxs = HtmlXPathSelector()
        reader = csv.DictReader(f)
        self.matched = set()
        for row in reader:
            self.matched.add(row['url'])

        for url in self.matched:
            yield Request(url, self.parse_product)

        with open(os.path.join(HERE, 'screwfix_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['url'] not in self.matched:
                    loader = ProductLoader(selector=hxs, item=Product())
                    loader.add_value('url', row['url'])
                    loader.add_value('sku', row['sku'].decode('utf-8'))
                    loader.add_value('identifier', row['identifier'].decode('utf-8'))
                    loader.add_value('name', row['name'].decode('utf-8'))
                    loader.add_value('price', row['price'])
                    yield loader.load_item()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        price = hxs.select('//span[@itemprop="price"]/text()').re(r'[\d.,]+')[0].replace(',', '')
        price = ceil(Decimal(price) / Decimal('1.2') * 100) / 100

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        loader.add_value('price', price)
        loader.add_xpath('identifier', '//span[@itemprop="productID"]/text()')

        yield loader.load_item()

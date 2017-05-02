import os
import shutil
from datetime import datetime
import StringIO
import csv

from scrapy import signals
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy import log
HERE = os.path.abspath(os.path.dirname(__file__))

class BigBaseSpider(BaseSpider):
    allowed_domains = []
    website_id = None

    def __init__(self, *args, **kwargs):
        super(BigBaseSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        if 'competitormonitor.com' not in self.allowed_domains:
            self.allowed_domains.append('competitormonitor.com')

    def parse_full(self, response):
        raise NotImplementedError("Subclass must implement this!")

    def parse_product(self, response):
        raise NotImplementedError("Subclass must implement this!")

    def start_requests_full(self):
        raise NotImplementedError("Subclass must implement this!")

    def start_requests(self):
        if self.full_run_required():
            start_req = self.start_requests_full()
            log.msg('Full run')
        else:
            start_req = self._start_requests_simple()
            log.msg('Simple run')

        for req in start_req:
            yield req

    def spider_closed(self, spider):
        if spider.name == self.name:
            shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(HERE, '%d.csv' % self.website_id))

    def _start_requests_simple(self):
        yield Request('http://competitormonitor.com/login.html?action=get_products_api&website_id=%d&matched=1' % self.website_id,
                      callback=self.parse_simple)

    def full_run_required(self):
        if not os.path.exists(os.path.join(HERE, '%d.csv' % self.website_id)):
            return True

        #run full only on Mondays
        return datetime.now().weekday() == 1
 
    def parse_simple(self, response):
        f = StringIO.StringIO(response.body)
        hxs = HtmlXPathSelector()
        reader = csv.DictReader(f)
        self.matched = set()
        for row in reader:
            self.matched.add(row['url'])

        for url in self.matched:
            yield Request(url, self.parse_product)

        with open(os.path.join(HERE, '%d.csv' % self.website_id)) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['url'] not in self.matched:
                    loader = ProductLoader(selector=hxs, item=Product())
                    loader.add_value('url', row['url'])
                    loader.add_value('sku', row['sku'].decode('utf-8'))
                    loader.add_value('identifier', row['identifier'].decode('utf-8'))
                    loader.add_value('name', row['name'].decode('utf-8'))
                    loader.add_value('price', row['price'])
                    loader.add_value('category', row['category'].decode('utf-8'))
                    loader.add_value('brand', row['brand'].decode('utf-8'))
                    loader.add_value('image_url', row['image_url'])
                    loader.add_value('shipping_cost', row['shipping_cost'])
                    yield loader.load_item()

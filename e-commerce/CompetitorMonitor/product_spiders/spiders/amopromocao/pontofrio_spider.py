import csv
import os
import shutil
from datetime import datetime
import StringIO

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import CloseSpider
from scrapy import signals

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))

class PontoFrioSpider(BaseSpider):
    name = 'pontofrio.com.br'
    allowed_domains = ['pontofrio.com.br', 'competitormonitor.com']

    def __init__(self, *args, **kwargs):
        super(PontoFrioSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

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
                        os.path.join(HERE, 'pontofrio_products.csv'))

    def _start_requests_full(self):
        yield Request('http://www.pontofrio.com.br', callback=self.parse_full)

    def _start_requests_simple(self):
        yield Request('http://competitormonitor.com/login.html?action=get_products_api&website_id=471524&matched=1', #471524 live website_id
                      callback=self.parse_simple)

    def full_run_required(self):
        if not os.path.exists(os.path.join(HERE, 'pontofrio_products.csv')):
            return True

        #full run only on Mondays
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

        with open(os.path.join(HERE, 'pontofrio_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['url'] not in self.matched:
                    loader = ProductLoader(selector=hxs, item=Product())
                    loader.add_value('url', row['url'])
                    loader.add_value('sku', row['sku'])
                    loader.add_value('identifier', row['identifier'])
                    loader.add_value('name', row['name'].decode('utf'))
                    loader.add_value('price', row['price'])
                    yield loader.load_item()

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)
        categories =  hxs.select('//ul[@class="headerMenu"]/li/a/@href').extract()
        for category in categories:
            yield Request(category, callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        sub_cats = hxs.select('//div[@class="navigation"]/div/h3/a/@href').extract()
        for sub_cat in sub_cats:
            yield Request(sub_cat, callback=self.parse_subcategories)

    def parse_subcategories(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="hproduct"]')
        if products:
            for product in products:
                loader = ProductLoader(item=Product(), selector=product)
                loader.add_xpath('name', 'a/strong[@class="name fn"]/text()')
                loader.add_xpath('url', 'a/@href')
                loader.add_xpath('identifier', 'a/@href')
                price = ''.join(product.select('a/span/span[@class="for price sale"]/strong/text()').extract()).replace('.','').replace(',','.')
                loader.add_value('price', price)
                yield loader.load_item()
        next = hxs.select('//li[@class="next"]/a/@href').extract()
        if next:
            url =  urljoin_rfc(get_base_url(response), next[0])
            yield Request(url, callback=self.parse_subcategories)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        price = ''.join(hxs.select('//span[@class="productDetails"]/span[@class="for"]' + 
                                       '/strong/i[@class="sale price"]/text()').extract()).replace('.','').replace(',','.')
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_value('identifier', response.url)
        loader.add_xpath('name', '//div[@class="produtoNome"]/h1/b/text()')
        yield loader.load_item()

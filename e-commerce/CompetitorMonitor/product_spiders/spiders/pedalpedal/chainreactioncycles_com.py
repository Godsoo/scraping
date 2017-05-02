import csv
import os
import shutil
from datetime import datetime
import StringIO

from scrapy.spider import BaseSpider
from scrapy import signals
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import CloseSpider

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy import log

from product_spiders.utils import extract_price
HERE = os.path.abspath(os.path.dirname(__file__))

class ChainReactionCyclesComSpider(BaseSpider):
    name = 'chainreactioncycles.com'
    allowed_domains = ['chainreactioncycles.com', 'competitormonitor.com']

    def __init__(self, *args, **kwargs):
        super(ChainReactionCyclesComSpider, self).__init__(*args, **kwargs)
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
            shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(HERE, 'chainreactioncycles_products.csv'))

    def _start_requests_full(self):
        yield Request('http://www.chainreactioncycles.com/Sitemap.aspx', callback=self.parse_full)

    def _start_requests_simple(self):
        yield Request('http://competitormonitor.com/login.html?action=get_products_api&website_id=484946&matched=1',
                      callback=self.parse_simple)

    def full_run_required(self):
        if not os.path.exists(os.path.join(HERE, 'chainreactioncycles_products.csv')):
            return True

        # run full only on Mondays
        return datetime.now().weekday() == 1

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//table[@class="Table43"]//a[contains(@href,"CategoryID")]/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//a[@class="Link88"]/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product)

        for next_page in hxs.select(u'//div[@class="Pager3"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), next_page)
            yield Request(url, callback=self.parse_product_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//h1//text()')

        product_loader.add_xpath('category', u'normalize-space(//a[@class="Link21" and position()=2]/text())')
        product_loader.add_xpath('brand', u'//a[@id="ModelsDisplayStyle4_HlkSeeAllBrandProducts"]/@title')

        img = hxs.select(u'//div[@id="DivModelImage"]/a/@href').extract()
        if not img:
            img = hxs.select(u'//div[@id="DivModelImage"]/a/img/@src').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        product_loader.add_xpath('brand', u'//span[@itemprop="manufacturer"]/text()')
#            product_loader.add_xpath('shipping_cost', '')
        product = product_loader.load_item()
        for option in hxs.select(u'//div[@id="TabContentAddToBasketTab"]//tr[@class="BackGround15"]'):
            prod = Product(product)
            prod['identifier'] = option.select(u'normalize-space(./td[1]/text())').extract()[0]
            prod['sku'] = option.select(u'normalize-space(./td[1]/text())').extract()[0]

            if option.select(u'./td[position()=1 and @colspan="4"]'):
                continue
            elif option.select(u'./td[4]//td[1]/text()').extract():
                prod['name'] = prod['name'].strip() + ' ' + option.select(u'normalize-space(./td[3]/a/text())').extract()[0]
                prod['price'] = extract_price(option.select(u'./td[4]//td[1]/text()').extract()[0])
            elif option.select(u'./td[6]//td[1]/text()').extract():
                prod['name'] = prod['name'].strip() + ' ' + option.select(u'normalize-space(./td[4]/a/text())').extract()[0]
                prod['price'] = extract_price(option.select(u'./td[6]//td[1]/text()').extract()[0])
                prod['identifier'] = option.select(u'normalize-space(./td[2]/text())').extract()[0]
                prod['sku'] = option.select(u'normalize-space(./td[2]/text())').extract()[0]
            elif option.select(u'./td[3]//td[1]/text()').extract():
                prod['price'] = extract_price(option.select(u'./td[3]//td[1]/text()').extract()[0])
            else:
                continue
            if prod['identifier'].strip():
                yield prod

    def parse_simple(self, response):
        f = StringIO.StringIO(response.body)
        hxs = HtmlXPathSelector()
        reader = csv.DictReader(f)
        self.matched = set()
        for row in reader:
            self.matched.add(row['url'])

        for url in self.matched:
            yield Request(url, self.parse_product)

        with open(os.path.join(HERE, 'chainreactioncycles_products.csv')) as f:
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

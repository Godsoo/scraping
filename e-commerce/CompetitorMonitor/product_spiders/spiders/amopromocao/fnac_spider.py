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

class FnacSpider(BaseSpider):
    name = 'fnac.com.br'
    allowed_domains = ['fnac.com.br', 'competitormonitor.com']

    def __init__(self, *args, **kwargs):
        super(FnacSpider, self).__init__(*args, **kwargs)
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
                        os.path.join(HERE, 'fnac_products.csv'))

    def _start_requests_full(self):
        yield Request('http://www.fnac.com.br', callback=self.parse_full)

    def _start_requests_simple(self):
        yield Request('http://competitormonitor.com/login.html?action=get_products_api&website_id=471520&matched=1', #471520 live website_id
                      callback=self.parse_simple)

    def full_run_required(self):
        if not os.path.exists(os.path.join(HERE, 'fnac_products.csv')):
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

        with open(os.path.join(HERE, 'fnac_products.csv')) as f:
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
        categories = hxs.select('//*[@id="menuCategorias"]/ul/li/a/@href').extract()
        for category in categories:
            url =  urljoin_rfc(get_base_url(response), category)
            req = Request(url, callback=self.parse_categories)
            req.cookies['QtdProdutosPagina'] = '18'
            yield req

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        sub_cats = hxs.select('//*[@id="menuBanner"]/div/div/div[@class="col"]/a/@href').extract()
        for sub_cat in sub_cats:
            url =  urljoin_rfc(get_base_url(response), sub_cat)
            req = Request(url+'?pagina=1', callback=self.parse_subcategories, meta={'page':1})
            req.cookies['QtdProdutosPagina'] = '18'
            yield req

    def parse_subcategories(self, response):
        BASE_URL = 'http://www.fnac.com.br'
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="produtos"]/div[@class="item"]')
        if products:
            for product in products:
                loader = ProductLoader(item=Product(), selector=product)
                loader.add_xpath('name', 'div[@class="nome"]/a[not(@class)]/text()')
                loader.add_xpath('url', 'div[@class="nome"]/a[not(@class)]/@href')
                loader.add_xpath('identifier', 'div[@class="nome"]/a[not(@class)]/@href')
                price = ''.join(product.select('div[@class="preco"]/span[@class="atual"]/text()').extract()).replace('.','').replace(',','.')
                loader.add_value('price', price)
                yield loader.load_item()
        next = hxs.select('//*[@id="aspnetForm"]/@action').extract()
        if next:
            next = ''.join(next[0].rpartition('=')[0:-1])
            next = ''.join((next, str(response.meta['page']+1)))
            url =  urljoin_rfc(BASE_URL, next)
            req = Request(url, callback=self.parse_subcategories, meta={'page':response.meta['page']+1})
            req.cookies['QtdProdutosPagina'] = '18'
            yield req

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        price = ''.join(hxs.select('//*[@id="cellPreco"]/span[@id="spanValorAtual"]/text()').extract()).replace('.','').replace(',','.')
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_value('identifier', response.url)
        loader.add_xpath('name', '//*[@id="nomeProduto"]/text()')
        yield loader.load_item()

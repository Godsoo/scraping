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

class AmericanasSpider(BaseSpider):
    name = 'americanas.com.br'
    allowed_domains = ['americanas.com.br']
    #start_urls = ['http://www.americanas.com.br/estaticapop/menu-todos-departamentos-teste']
    start_urls = ['http://www.americanas.com.br']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        #categories = hxs.select('//a[@class="sDeptLink"]/@href').extract() + hxs.select('//li[@class="line"]/strong/a/@href').extract()
        categories = hxs.select('//div[@class="allDpt"]/div/ul/li/ul/li/ul/li/a/@href').extract()
        for category in categories:
            yield Request(category, callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        sub_cats = hxs.select('//li[@class="li"]/h2/a[@rel!="nofollow"]/@href').extract()
        for sub_cat in sub_cats:
            url =  urljoin_rfc(get_base_url(response), sub_cat)
            yield Request(url, callback=self.parse_subcategories)
        sub_cats = hxs.select('//li[@class="li"]/h2/a[@rel="nofollow"]/@href').extract()
        for sub_cat in sub_cats:
            url =  urljoin_rfc(get_base_url(response), sub_cat)
            yield Request(url, callback=self.parse_categories)

    def parse_subcategories(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="prods"]/ul[@class="pList"]/li/div[@class="hproduct"]')        
        if products:
            for product in products:
                loader = ProductLoader(item=Product(), selector=product)
                name = ''.join(product.select('a[@class="url"]/span/strong[@class="n name fn"]/text()').extract())
                loader.add_value('name', name)
                url = urljoin_rfc(get_base_url(response),  product.select('a[@class="url"]/@href').extract()[0])
                loader.add_value('url', url.decode('utf'))
                loader.add_value('identifier', url.decode('utf'))
                price = ''.join(product.select('a[@class="url"]/span/span/span[@class="sale price"]/text()').extract()).replace('.','').replace(',','.')
                loader.add_value('price', price)
                yield loader.load_item()
            next = hxs.select('//ul[@class="pag acr"]/li')[-2].select('a/@href').extract()
            if next:
                url =  urljoin_rfc(get_base_url(response), next[0])
                yield Request(url, callback=self.parse_subcategories)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        price = ''.join(hxs.select('//p[@class="sale price"]/strong/span[@class="amount"]/text()').extract()).replace('.','').replace(',','.')
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_value('identifier', response.url)
        loader.add_xpath('name', '//div[@class="hproduct"]/div/div/h1[@class="title"]/strong/text()')
        yield loader.load_item()


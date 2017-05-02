import os
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.fuzzywuzzy import process
from product_spiders.fuzzywuzzy import fuzz

HERE = os.path.abspath(os.path.dirname(__file__))

class RicardoEletroSpider(BaseSpider):
    name = 'ricardoeletro.com.br'
    allowed_domains = ['ricardoeletro.com.br']
    start_urls = ['http://www.ricardoeletro.com.br']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//*[@id="CategoriasHeader"]/div/div/div[@class="loja "]/a/@href').extract()
        for category in categories:
            yield Request(category, callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        sub_cats = hxs.select('//*[@id="CategoriasLeft"]/div/div/ul/li/a/@href').extract()
        for sub_cat in sub_cats:
            yield Request(sub_cat, callback=self.parse_subcategories)

    def parse_subcategories(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="box-vitrine content-produto"]')
        if products:
            for product in products:
                loader = ProductLoader(item=Product(), selector=product)
                loader.add_xpath('name', 'div[@class="nome-produto-vertical"]/a/text()')
                loader.add_xpath('url', 'div[@class="nome-produto-vertical"]/a/@href')
                price = ''.join(product.select('div/div/span[@class="produto-por"]/text()').extract()).replace('.','').replace(',','.')
                loader.add_value('price', price)
                yield loader.load_item()
        next = hxs.select('//a[@class="avancar "]/@href').extract()
        if next:
            yield Request(next[0], callback=self.parse_subcategories)

        #sub_cats = hxs.select('//span[@class="subcategories"]/span/span/a/@href').extract()
        #for sub_cat in sub_cats:
        #    url =  urljoin_rfc(get_base_url(response), sub_cat)
        #    yield Request(url, callback=self.parse_categories)

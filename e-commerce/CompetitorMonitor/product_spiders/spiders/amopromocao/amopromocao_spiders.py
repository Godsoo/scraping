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

class AmoPromocaoSpider(BaseSpider):
    name = 'amopromocao.com.br'
    allowed_domains = ['amopromocao.com.br']
    start_urls = ['http://www.amopromocao.com.br']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories =  hxs.select('//*[@id="menuSuperior"]/ul/li/a/@href').extract()
        for category in categories:
            url =  urljoin_rfc(get_base_url(response), category.replace('../','/'))
            yield Request(url, callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//*[@id="listasProdutos"]/ul/li[@class="produtos"]')
        if products:
            for product in products:
                loader = ProductLoader(item=Product(), selector=product)
                loader.add_value('name', product.select('a/h3[@class="nomeProduto"]/text()').extract()[0].strip())
                url = urljoin_rfc(get_base_url(response),  product.select('a/@href').extract()[0])
                loader.add_value('url', url)
                price = ''.join(product.select('a/p[@class="valorPor"]/text()').extract()).replace('.','').replace(',','.')
                #if not price:
                #    price = ''.join(product.select('span/span/span/text()').extract()).replace('.','').replace(',','.')
                loader.add_value('price', price)
                yield loader.load_item()
        #sub_cats = hxs.select('//span[@class="subcategories"]/span/span/a/@href').extract()
        #for sub_cat in sub_cats:
        #    url =  urljoin_rfc(get_base_url(response), sub_cat)
        #    yield Request(url, callback=self.parse_categories)

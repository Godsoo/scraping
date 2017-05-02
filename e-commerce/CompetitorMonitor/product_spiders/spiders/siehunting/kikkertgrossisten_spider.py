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

class KikkertgrossistenSpider(BaseSpider):
    name = 'kikkertgrossisten.dk'
    allowed_domains = ['kikkertgrossisten.dk']
    start_urls = ['http://www.kikkertgrossisten.dk']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories =  hxs.select('//div[@class="products_menu"]/ul/li/a/@href').extract()
        for category in categories:
            url =  urljoin_rfc(get_base_url(response), category)
            yield Request(url, callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="productlist section"]/table/tr')
        if products:
            for product in products:
                loader = ProductLoader(item=Product(), selector=product)
                loader.add_xpath('name', 'td[@class="desc"]/strong/a/text()')
                url = urljoin_rfc(get_base_url(response), product.select('td[@class="desc"]/strong/a/@href').extract()[0])
                loader.add_value('url', url)
                price = ''.join(product.select('td[@class="desc"]/div[@class="current price offer"]/span[@class="first"]/text()').extract()).replace('.','').replace(',','.')
                
                if not price:
                    price = ''.join(product.select('td[@class="desc"]/'
                                               'div[@class="current price"]/'
                                               'span[@class="first"]/text()').extract()).replace('.','').replace(',','.')
                loader.add_value('price', price)
                yield loader.load_item()
        sub_cats = hxs.select('//table[@class="p"]/tbody/tr/td//strong/a/@href').extract()
        if not sub_cats:
            sub_cats = hxs.select('//ul[@class="subcategories"]/li/a/@href').extract()
            if not sub_cats:
                sub_cats = hxs.select('//table[@class="p"]/tbody/tr/td//a/@href').extract()
                if not sub_cats:
                    sub_cats = hxs.select('//li[@class="active"]/ul/li/a/@href').extract()
        for sub_cat in sub_cats:
            url =  urljoin_rfc(get_base_url(response), sub_cat)
            yield Request(url, callback=self.parse_categories)

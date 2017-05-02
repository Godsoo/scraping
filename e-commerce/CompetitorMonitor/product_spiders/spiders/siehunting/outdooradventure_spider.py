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

class outdoorAdventureSpider(BaseSpider):
    name = 'outdooradventure.dk'
    allowed_domains = ['outdooradventure.dk']
    start_urls = ['http://outdooradventure.dk']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories =  hxs.select('//*[@id="ja-sidenav"]/li/a/@href').extract()# + hxs.select('//*[@id="ja-sidenav"]/li/ul/li/a/@href').extract()
        for category in categories:
            yield Request(category+'?limit=all', callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//li[@class="item  center " or @class="item  first " or @class="item  last "]')
        if products:
            for product in products:
                loader = ProductLoader(item=Product(), selector=product)
                loader.add_xpath('name', 'h5/a/text()')
                #url = urljoin_rfc(get_base_url(response),  product.select('span/h6/a/@href').extract()[0])
                loader.add_xpath('url', 'h5/a/@href')
                price = ''.join(product.select('div[@class="price-form clearfix"]/div/span/span[@class="price"]/text()').extract()).replace('.','').replace(',','.')
                if not price:
                    price = ''.join(product.select('div[@class="price-form clearfix"]/div/p[@class="special-price"]/span[@class="price"]/text()').extract()).replace('.','').replace(',','.')
                loader.add_value('price', price)
                yield loader.load_item()
        sub_cats = hxs.select('//dl[@id="narrow-by-list2"]/dd/ol/li/a/@href').extract()
        for sub_cat in sub_cats:
            yield Request(sub_cat, callback=self.parse_categories)

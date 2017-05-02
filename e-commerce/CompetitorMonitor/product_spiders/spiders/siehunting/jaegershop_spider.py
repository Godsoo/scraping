import os
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class JaegerShopSpider(BaseSpider):
    name = 'jaegershop.dk'
    allowed_domains = ['jaegershop.dk']
    start_urls = ['http://www.jaegershop.dk/index.php?main_page=products_all']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="tie-indent"]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('name', 'div/div/a[@class="name"]/strong/text()')
            loader.add_xpath('url', 'div/div/a[@class="name"]/@href')
            price = ''.join(product.select('div/div/span[@class="price"]/text()').extract()).replace('.','').replace(',','.')
            if not price or price == u'\xa0':
                price = ''.join(product.select('div/div/span[@class="price"]/span[@class="productSpecialPrice"]/text()').extract()).replace('.','').replace(',','.')
            loader.add_value('price', price)
            yield loader.load_item()
        next = hxs.select('//a[@title=" N\xc3\xa6ste side "]/@href'.decode('utf')).extract()
        if next:
            yield Request(next[-1])

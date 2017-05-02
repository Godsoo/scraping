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

class HighendOpticsSpider(BaseSpider):
    name = 'highend-optics.dk'
    allowed_domains = ['highend-optics.dk']
    start_urls = ['http://www.highend-optics.dk/all-products.php']

    """def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories =  hxs.select('//td[@class="boxText"]/a/@href').extract()
        for category in categories:
           yield Request(category, callback=self.parse_categories)"""

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//table[@class="productListing"]/tr[@class]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('name', 'td//td[@class="productListName"]/a/text()')
            loader.add_xpath('url', 'td//td[@class="productListName"]/a/@href')
            price = ''.join(product.select('td//td[@class="productListSpecialPrice"]/text()').extract()).replace('.','').replace(',','.')
            if not price:
                price = ''.join(product.select('td//td[@class="productListPrice"]/text()').extract()).replace('.','').replace(',','.')
            loader.add_value('price', price)
            yield loader.load_item()
        next = hxs.select('//a[@class="pageResults" and @title=" N\xc3\xa6ste > "]/@href'.decode('utf')).extract()
        if next:
            yield Request(next[-1])

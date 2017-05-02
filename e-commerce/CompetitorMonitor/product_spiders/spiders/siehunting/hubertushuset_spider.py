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

class HubertushusetSpider(BaseSpider):
    name = 'hubertushuset.com'
    allowed_domains = ['hubertushuset.com']
    start_urls = ['http://www.hubertushuset.com/products/productlist.aspx?searchtext=+']


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="prelement"]')
        if products:
            for product in products:
                loader = ProductLoader(item=Product(), selector=product)
                loader.add_xpath('name', 'div[@class="prmain"]/a/text()')
                url = urljoin_rfc(get_base_url(response),  product.select('div[@class="prmain"]/a/@href').extract()[0])
                loader.add_value('url', url)
                price = ''.join(product.select('div[@class="prbasket"]/p[@class="prpri"]/text()').extract()).replace('.','').replace(',','.')
                loader.add_value('price', price)
                yield loader.load_item()
        next = hxs.select('//a[@class="plistpagnext"]/@href').extract()
        if next:
            url =  urljoin_rfc(get_base_url(response), next[-1])
            yield Request(url)

import os
import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.fuzzywuzzy import process
from product_spiders.fuzzywuzzy import fuzz

HERE = os.path.abspath(os.path.dirname(__file__))

class MagazineLuizaSpider(BaseSpider):
    name = 'magazineluiza.com.br'
    allowed_domains = ['magazineluiza.com.br']
    start_urls = ['http://www.magazineluiza.com.br/busca//?itens=1000']

    def parse(self, response):
        idx = 1
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="product"]')
        if products:
            for product in products:
                loader = ProductLoader(item=Product(), selector=product)
                loader.add_xpath('name', 'a/span/span[@class="productTitle"]/text()')
                url = urljoin_rfc(get_base_url(response),  product.select('a/@href').extract()[0])
                m = re.search('/p/(\d+)/',url)
                if m:
                    prod_id = m.group(1)
                else:
                    prod_id = 'p' + str(idx)
                    idx = idx + 1
                loader.add_value('identifier', prod_id)
                loader.add_value('url', url)
                price = ''.join(product.select('a/span/span/span[@class="price"]/text()').extract()).replace('.','').replace(',','.')
                loader.add_value('price', price)
                yield loader.load_item()
            next = hxs.select('//a[@class="forward"]/@href').extract()
            if next:
                url =  urljoin_rfc(get_base_url(response), next[0])
                yield Request(url)

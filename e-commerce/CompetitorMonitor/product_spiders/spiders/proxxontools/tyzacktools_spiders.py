import os
import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class TyzackToolsSpider(BaseSpider):
    name = 'tyzacktools.com'
    allowed_domains = ['tyzacktools.com']
    start_urls = ['http://www.tyzacktools.com/manufacturer/23-proxxon.aspx',
                  'http://www.tyzacktools.com/manufacturer/38-proxxon.aspx']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="product-item"]')
        if products:
            for product in products:
                url = product.select('h2/a/@href').extract()[0]
                price = ''.join(product.select('div/div[@class="prices"]/span[@class="productPrice"]/text()').extract())
                name = ''.join(product.select('h2/a/text()').extract())
                if 'From' in price:
                    yield Request(url, callback=self.parse_product, meta={'name':name})
                else:
                    loader = ProductLoader(item=Product(), selector=product)
                    loader.add_value('name', name)
                    loader.add_value('identifier', name)
                    loader.add_value('url', url)
                    loader.add_value('price', float(re.findall("\d+.\d+",price)[0])/1.2)
                    yield loader.load_item()
        next = hxs.select('//div[@class="product-pager"]/div/a[text()="Next"]/@href').extract()
        if next:
            yield Request(next[0])

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="product-variant-line"]')
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', response.meta['name'])
        loader.add_value('identifier', response.meta['name'])
        loader.add_value('url', response.url)
        price = products[0].select('div[@class="price"]/span[@class="productPrice"]/text()').extract()[0]
        loader.add_value('price', float(re.findall("\d+.\d+",price)[0])/1.2)   
        yield loader.load_item()
        for product in products[1:]:
            loader = ProductLoader(item=Product(), selector=product)
            name = ''.join(product.select('div/div[@class="productname"]/text()').extract()).strip()
            loader.add_value('name', name)
            loader.add_value('identifier', name)
            loader.add_value('url', response.url)
            price = product.select('div[@class="price"]/span[@class="productPrice"]/text()').extract()[0]
            loader.add_value('price', float(re.findall("\d+.\d+",price)[0])/1.2)   
            yield loader.load_item()
            


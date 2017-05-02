import os
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class JoesAquaticWorldSpider(BaseSpider):
    name = 'joesaquaticworld.co.uk'
    allowed_domains = ['joesaquaticworld.co.uk']
    start_urls = ['http://www.joesaquaticworld.co.uk']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//*[@id="sidelinks"]/ul/li/a/@href').extract()
        for category in categories:
            yield Request(category+'?limit=all', callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@ class="category-products"]/ul/li')
        if products:
            for product in products:
                url = ''.join(product.select('h2/a/@href').extract())
                price = ''.join(product.select('div[@class="price-box"]/p[@class="special-price"]/span[@class="price"]/text()').extract())
                identifier = product.select('.//button/@onclick').re(r"product/(.*)/'")[0]
                if price:
                    loader = ProductLoader(item=Product(), selector=product)   
                    loader.add_xpath('name', 'h2/a/text()')
                    loader.add_value('url', url)
                    loader.add_value('price', price)
                    loader.add_value('identifier', identifier)
                    yield loader.load_item()
                else:
                    yield Request(url, callback=self.parse_details)
        else:
            sub_categories = hxs.select('//div[@class="subcategory-holder"]/div/a/@href').extract()
            for sub_category in sub_categories:
                yield Request(sub_category + '?limit=all', callback=self.parse_products)

    def parse_details(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="product-shop"]/table/tbody/tr')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('name', 'td[not(@class)]/text()')
            loader.add_value('url', response.url)
            price = ''.join(product.select('td[@class="a-right"]/div[@class="price-box"]/p[@class="special-price"]/span[@class="price"]/text()').extract())
            if not price:
                price = ''.join(product.select('td[@class="a-right"]/div[@class="price-box"]/span[@class="regular-price"]/span[@class="price"]/text()').extract())
            loader.add_value('price', price)
            identifier = product.select('.//input/@name').re(r'super_group\[(.*)\]')[0]
            loader.add_value('identifier', identifier)
            yield loader.load_item()

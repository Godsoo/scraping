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

class EzzenceSpider(BaseSpider):
    name = 'beautycos-ezzence.dk'
    allowed_domains = ['ezzence.dk']
    start_urls = ['http://ezzence.dk/maerkeraz']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//*[@id="maerkeraz"]/ul/li/a/@href').extract()
        for category in categories:
            yield Request(category + '?limit=all', callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//ul[@class="products-grid"]/li')
        if products:
            for product in products:
                yield Request(
                        product.select('div/div/h2[@class="product-name"]/a/@href').extract()[0],
                        callback=self.parse_product,
                        meta={
                            'brand':''.join(hxs.select('//p[@class="category-image"]/img/@title').extract()),
                        })

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        code = hxs.select('//form[@id="product_addtocart_form"]/@action').extract()[0].split('/')
        code = code[code.index('product') + 1]
        product_loader.add_value('identifier', code)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//h1/text()')
        product_loader.add_value('brand', response.meta.get('brand'))
        price = hxs.select('//span[@id="product-price-' + code + '"]/text()').extract()[0]\
            .strip().replace('.', '').replace(',', '.')
        if not price:
            price = hxs.select('//span[@id="product-price-' + code + '"]/*/text()').extract()[0]\
                .strip().replace('.', '').replace(',', '.')
        product_loader.add_value('price', price)
        product_loader.add_value('sku', code)
        product_loader.add_value('category', response.meta.get('brand'))
        img = hxs.select(u'//img[@id="image"]/@src').extract()
        if not img:
            img = hxs.select(u'//div[@class="image"]/@style').extract()[0].split('(')[1].split(')')
        product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        yield product_loader.load_item()

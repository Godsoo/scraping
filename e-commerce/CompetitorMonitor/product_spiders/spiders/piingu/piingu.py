"""
Name: piingu-piingu.dk
Account: Piingu
Ticket: https://app.assembla.com/spaces/competitormonitor/tickets/5045

"""

from scrapy.selector import XmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy import Spider

class PiinguSpider(Spider):
    name = 'piingu-piingu.dk'
    allowed_domains = ['piingu.dk']
    start_urls = ('https://www.piingu.dk/google-shopping.xml',)

    def parse(self, response):
        xxs = XmlXPathSelector(response)
        xxs.register_namespace("g", "http://base.google.com/ns/1.0")
        products = xxs.select('//channel/item')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('url', 'link/text()')
            loader.add_xpath('name', 'title/text()')
            loader.add_xpath('image_url', 'g:image_link/text()')
            loader.add_xpath('price', 'g:price/text()')
            loader.add_xpath('brand', 'g:brand/text()')
            categories = product.select('g:product_type/text()').extract()[0].split(' &gt; ')
            loader.add_value('category', categories)
            loader.add_xpath('sku', 'g:id/text()')
            loader.add_xpath('identifier', 'g:id/text()')
            stock = product.select('g:availability/text()').extract()[0].lower()
            if stock != 'in stock':
                loader.add_value('stock', 0)
            yield loader.load_item()

import os

from scrapy.contrib.spiders import XMLFeedSpider
from scrapy.http import XmlResponse

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class CocopandaSpider(XMLFeedSpider):
    name = 'cocopanda.dk'
    allowed_domains = ['cocopanda.dk']
    start_urls = ('http://www.cocopanda.dk/kelkoo.xml',)
    itertag = 'product'

    def parse_node(self, response, node):
        if not isinstance(response, XmlResponse):
            return

        identifier = node.select(u'./product-url/text()').re(r'product/([^/]+)/')
        identifier = identifier[0]

        loader = ProductLoader(item=Product(), selector=node)
        url = node.select(u'./product-url/text()').extract()[0]
        loader.add_value('url', url)
        loader.add_xpath('name', u'./title/text()')
        price = node.select(u'./price/text()').extract()[0].replace(',', '.')
        loader.add_value('price', price)
        loader.add_xpath('category', u'merchant-category/text()')
        loader.add_xpath('brand', u'brand/text()')
        loader.add_xpath('image_url', u'image-url/text()')
        loader.add_value('sku', identifier)
        loader.add_value('identifier', identifier)
        if loader.get_output_value('price'):
            return loader.load_item()
        else:
            return Product()

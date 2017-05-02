import os
import json

from scrapy.contrib.spiders import XMLFeedSpider
from scrapy.http import XmlResponse

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class GuitarHusetpider(XMLFeedSpider):
    name = 'gitarhuset.no'
    allowed_domains = ['gitarhuset.no']
    start_urls = ('http://www.gitarhuset.no/kelkoo.xml',)
    itertag = 'product'

    def parse_node(self, response, node):
        if not isinstance(response, XmlResponse):
            return

        identifier = node.select(u'./product-url/text()').re(r'product/([^/]+)/')
        identifier = identifier[0]

        loader = ProductLoader(item=Product(), selector=node)
        loader.add_xpath('url', u'./product-url/text()')
        loader.add_xpath('name', u'./title/text()')
        price = node.select(u'./price/text()').extract()[0].replace(',', '.')
        loader.add_value('price', price)
        loader.add_xpath('category', u'merchant-category/text()')
        loader.add_xpath('image_url', u'image-url/text()')
        loader.add_value('sku', identifier)
        loader.add_value('identifier', identifier)
        log.msg(json.dumps({'name': loader.get_output_value('name'), 'price': price}))
        if loader.get_output_value('price'):
            return loader.load_item()
        else:
            return Product()
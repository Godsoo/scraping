import os

import HTMLParser

from scrapy.contrib.spiders import XMLFeedSpider
from scrapy.http import XmlResponse
from product_spiders.spiders.BeautifulSoup import BeautifulSoup

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from decimal import Decimal

HERE = os.path.abspath(os.path.dirname(__file__))

class SieHuntingSpider(XMLFeedSpider):
    name = 'sie-hunting.com'
    allowed_domains = ['sie-hunting.com']
    start_urls = ('http://sie-hunting.com/_source/modules/shop_priceindex/export.php?index=Competitor&iso=dk&site=1',)
    itertag = 'Product'

    def parse_node(self, response, node):
        loader = ProductLoader(item=Product(), selector=node)

        # soup = BeautifulSoup(node.extract())
        # loader.add_value('url', soup.url.text)

        # name = soup.title.text
        # h = HTMLParser.HTMLParser()
        # name = h.unescape(name)
        # loader.add_value('name', name)

        # discount = float(soup.discount.text)
        # price = float(soup.price.text)
        # loader.add_value('price', price - discount)

        # loader.add_value('identifier', soup.id.text + ':' + soup.number.text)
        # if loader.get_output_value('price'):
        #     return loader.load_item()
        # else:
        #     return Product()

        name = node.select('Title/text()').extract()[0]
        h = HTMLParser.HTMLParser()
        name = h.unescape(name)
        loader.add_value('name', name)

        loader.add_xpath('url', 'URL/text()')

        price = Decimal(node.select("Price/text()").extract()[0])
        discount = Decimal(node.select("Discount/text()").extract()[0])

        loader.add_value('price', price - discount)

        Id = node.select("Id/text()").extract()[0]
        number = node.select("Number/text()").extract()
        if number:
            number = number[0]
        else:
            number = ""

        loader.add_value('identifier', Id + number)

        if loader.get_output_value('price'):
            return loader.load_item()
        else:
            return Product()

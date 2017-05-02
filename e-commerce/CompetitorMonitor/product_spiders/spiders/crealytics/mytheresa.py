from decimal import Decimal
import os
import_error = False
try:
    import demjson
except ImportError:
    demjson = None

from scrapy.spider import BaseSpider
from scrapy.http import Request

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class MyTheresaSpider(BaseSpider):
    name = 'crealytics-mytheresa.com'
    allowed_domains = ['mytheresa.com']
    start_urls = ('http://www.mytheresa.com/en-gb/designers/y-3.html',
                  'http://www.mytheresa.com/en-gb/designers/adidas.html',
                  'http://www.mytheresa.com/en-gb/designers/gucci.html',
                  'http://www.mytheresa.com/en-gb/designers/givenchy.html',
                  'http://www.mytheresa.com/en-gb/designers/alexander-mcqueen.html',
                  'http://www.mytheresa.com/en-gb/designers/chloe.html',
                  'http://www.mytheresa.com/en-gb/designers/diane-von-furstenberg.html',
                  'http://www.mytheresa.com/en-gb/designers/valentino.html',
                  'http://www.mytheresa.com/en-gb/designers/burberry-brit.html',
                  'http://www.mytheresa.com/en-gb/designers/burberry-london.html',
                  'http://www.mytheresa.com/en-gb/designers/rag-bone.html',
                  'http://www.mytheresa.com/en-gb/designers/kenzo.html',
                  'http://www.mytheresa.com/en-gb/designers/y-3-sport.html',
                  'http://www.mytheresa.com/en-gb/designers/burberry-london-england.html')

    def start_requests(self):
        yield Request('http://www.mytheresa.com/en-gb/mzi18n/storeswitch/selectorredirect/?redirectPath=%2Fen-gb%2Fhome&country=GB',
                      callback=self.parse_currency)

    def parse_currency(self, response):
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        products = response.xpath('//h2[@class="product-name"]/a/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product)

        next_page = response.xpath('//li[@class="next"]/a[@title="Next"]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]))

    def parse_product(self, response):
        data = demjson.decode(response.xpath('//script[@type="application/ld+json"]/text()')[0].extract())[0]
        loader = ProductLoader(response=response, item=Product())
        loader.add_value('identifier', data['sku'])
        loader.add_value('sku', data['sku'])
        loader.add_value('name', data['name'])
        loader.add_value('brand', data['brand']['name'])
        loader.add_value('url', data['url'])
        loader.add_value('image_url', data['image'])
        categories = response.xpath('//div[@class="breadcrumbs"]/ul/li/a/span/text()')[1:].extract()
        for category in categories:
            loader.add_value('category', category)
        price = response.xpath('//div[@class="price-info"]//span[@class="price"]/text()').extract()
        loader.add_value('price', price)
        if price and extract_price(price[0]) <= Decimal('499'):
            loader.add_value('shipping_cost', '10.00')
        if response.xpath('//button[@class="button btn-cart soldout"]'):
            loader.add_value('stock', 0)
        yield loader.load_item()

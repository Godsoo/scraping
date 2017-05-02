import json
import copy

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.url import add_or_replace_parameter

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class SelfridgesSpider(BaseSpider):
    name = 'crealytics-selfridges.com'
    allowed_domains = ['selfridges.com']
    start_urls = ('http://www.selfridges.com/GB/en/cat/y3/',
                  'http://www.selfridges.com/GB/en/cat/adidas-by-stella-mccartney/',
                  'http://www.selfridges.com/GB/en/cat/gucci/',
                  'http://www.selfridges.com/GB/en/cat/givenchy/',
                  'http://www.selfridges.com/GB/en/cat/alexander-mcqueen/',
                  'http://www.selfridges.com/GB/en/cat/chloe/',
                  'http://www.selfridges.com/GB/en/cat/diane-von-furstenberg/',
                  'http://www.selfridges.com/GB/en/cat/valentino/',
                  'http://www.selfridges.com/GB/en/cat/paul-smith/',
                  'http://www.selfridges.com/GB/en/cat/burberry/',
                  'http://www.selfridges.com/GB/en/cat/rag-bone/',
                  'http://www.selfridges.com/GB/en/cat/kenzo/',
                  'http://www.selfridges.com/GB/en/cat/dan-ward/',
                  'http://www.selfridges.com/GB/en/cat/y-3-sport/',
                  'http://www.selfridges.com/GB/en/cat/paul-smith-accessories/',
                  'http://www.selfridges.com/GB/en/cat/rag-and-bone/')
    stock_url = 'http://www.selfridges.com/webapp/wcs/stores/servlet/AjaxStockStatusView?productId={}'

    def start_requests(self):
        yield Request('http://www.selfridges.com/GB/en/cat/CountrySelection/?countryCode=GB_en',
                      callback=self.parse_currency)

    def parse_currency(self, response):
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        products = response.xpath('//div[@class="productsInner"]//a[@class="title"]/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product)

        next_page = response.xpath('//div[@class="pageNumber"]//a[@class="arrow-right"]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]))

    def parse_product(self, response):
        name = response.xpath('//h1[@itemprop="name"]/text()').extract()[0]
        # colours = response.xpath('//label[@itemprop="color"]/input/@value').extract()
        identifier = response.xpath('//input[@type="hidden" and @name="productId"]/@value')[0].extract()
        loader = ProductLoader(response=response, item=Product())
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)

        price = response.xpath('//p[@class="price"]//span[@itemprop="price"]').extract()
        if price:
            loader.add_value('price', price)
        else:
            loader.add_value('price', '0.00')
            loader.add_value('stock', 0)
        loader.add_value('url', response.url)
        loader.add_xpath('image_url', '//div[@class="productImage"]//img[@itemprop="image"]/@src')
        brand = response.xpath('//p[@itemprop="brand"]/a/text()')[0].extract().strip()
        loader.add_value('brand', brand)
        categories = response.xpath('//ul[@itemprop="breadcrumb"]/li/a/text()')[1:].extract()
        for category in categories:
            loader.add_value('category', category)
        item = loader.load_item()

        sizes = response.xpath('//label/input[@name="Size"]/@value').extract()
        if len(sizes) > 1:
            for size in sizes:
                stock_url = add_or_replace_parameter(self.stock_url.format(identifier), 'attr', 'Size')
                stock_url = add_or_replace_parameter(stock_url, 'attrval', size)
                it = copy.deepcopy(item)
                # it['name'] += u' {}'.format(size)
                yield Request(stock_url,
                              meta={'item': it},
                              callback=self.parse_stock)
                break
        else:
            yield Request(self.stock_url.format(identifier),
                          meta={'item': item},
                          callback=self.parse_stock)

    def parse_stock(self, response):
        data = json.loads(response.body)
        item = response.meta.get('item')
        options = [option for option in data['stocks'] if option['name'] == 'Colour']
        for option in options:
            p = copy.deepcopy(item)
            p['identifier'] += u'-{}'.format(option['sku'])
            p['sku'] = option['sku']
            if not option['inStock']:
                p['stock'] = 0
            p['name'] += ' {}'.format(option['value'])
            yield p
        if not options:
            size_opts = [option for option in data['stocks'] if option['name'] == 'Size']
            if size_opts and not response.meta.get('size_parsed'):
                size = size_opts[0]['value']
                stock_url = add_or_replace_parameter(self.stock_url.format(item['identifier']), 'attr', 'Size')
                stock_url = add_or_replace_parameter(stock_url, 'attrval', size)
                yield Request(stock_url,
                              meta={'item': item,
                                    'size_parsed': True},
                              callback=self.parse_stock)
            else:
                yield item

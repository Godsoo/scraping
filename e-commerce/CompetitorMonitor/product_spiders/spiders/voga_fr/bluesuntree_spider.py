import re
import csv
import json
from StringIO import StringIO

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url

from decimal import Decimal

from utils import extract_price


class BluesuntreeSpider(BaseSpider):
    name = 'voga_fr-bluesuntree.co.uk'
    allowed_domains = ['bluesuntree.co.uk', 'xe.com']
    start_urls = ('http://www.xe.com/currencyconverter/convert/?Amount=1&From=GBP&To=EUR',)

    products_ids = {}

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        exchange_rate = hxs.select('//tr[@class="uccRes"]/td[last()]/text()').re('[\d\.]+')
        yield Request('http://www.bluesuntree.co.uk/',
                      meta={'exchange_rate': extract_price(exchange_rate[0])}, callback=self.parse_real)

    def parse_real(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[@class="product-listing"]//h3/a/@href').extract()
        for product in products:
            yield Request(product, callback=self.parse_product, meta=response.meta)

        products = hxs.select('//div[@class="product-listing"]//h3/a/@href').extract()
        for product in products:
            yield Request(product, callback=self.parse_product, meta=response.meta)

        next = hxs.select('//a[@class="next"]/@href').extract()
        if next:
            yield Request(next[0], callback=self.parse_real, meta=response.meta)

        if not products:
            categories = hxs.select('//li[contains(@class, "primary-nav__category")]/a/@href').extract()
            categories += hxs.select('//div[contains(@class, "grid")]//h3[@class="media__title"]/a/@href').extract()
            for category in categories:
                yield Request(category, callback=self.parse_real, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        name = hxs.select('//div[@id="product-info"]//h1/text()').extract()[0]
        identifier = hxs.select('//input[@name="product"]/@value').extract()[0]
        image_url = hxs.select('//figure[@class="hero__img"]/span/span/@data-src').extract()
        image_url = image_url[0] if image_url else ''
        categories = hxs.select('//ul[contains(@class, "breadcrumb")]/li/a/text()').extract()
        categories = [category for category in categories if category .upper() not in ('HOME', 'PRODUCTS')]
        sku = ''.join(hxs.select('//p[@class="panel__sku"]/text()').extract())
        brand = hxs.select('//div[@id="product-information-block-1"]//img[contains(@alt, "logo")]/@alt').re('(.*) logo')

        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            prices = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))
                        prices[product] = prices.get(product, 0) +  extract_price(option['price'])

        if options_config:
            for option_identifier, option_name in products.iteritems():
                loader = ProductLoader(response=response, item=Product())
                loader.add_value("identifier", identifier + '-' + option_identifier)
                loader.add_value('name', name + option_name)
                loader.add_value('image_url', image_url)
                price = (extract_price(product_data['basePrice'])+prices[option_identifier])*Decimal(1.20)
                loader.add_value('price', str(price * response.meta.get('exchange_rate')))
                loader.add_value('url', response.url)
                loader.add_value('brand', brand)
                loader.add_value('sku', sku)
                for category in categories:
                    loader.add_value('category', category)
                product = loader.load_item()
                if not product['price']:
                    product['stock'] = 0
                yield product
        else:
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('url', response.url)
            loader.add_value('name', name)
            loader.add_value('brand', brand)
            loader.add_value('image_url', image_url)
            loader.add_value('identifier', identifier)
            for category in categories:
                loader.add_value('category', category)
            loader.add_value('sku', sku)
            price = hxs.select('//div[@id="product-info"]//p[@class="special-price"]/span[@class="price"]/text()').extract()
            if not price:
                price = hxs.select('//div[@id="product-info"]//div[@class="price-box"]/span[@class="regular-price"]/span[@class="price"]/text()').extract()
            loader.add_value('price', str(extract_price(price[0]) * response.meta.get('exchange_rate')))
            product = loader.load_item()
            if not product['price']:
                product['stock'] = 0
            yield product
 

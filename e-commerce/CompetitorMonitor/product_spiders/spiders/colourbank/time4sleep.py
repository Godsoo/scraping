import os
import re
import json
import csv
import urlparse

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class Time4SleepSpider(BaseSpider):
    name = 'colourbank-time4sleep.co.uk'
    allowed_domains = ['time4sleep.co.uk']

    start_urls = ['http://www.time4sleep.co.uk']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[@id="nav"]//a/@href').extract()
        for category in categories:
            yield Request(category+'/where/limit/all', callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//h2/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        product_name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0]
        product_price = hxs.select('//div[contains(@class, "price-box")]//span[@itemprop="price"]/text()').extract()
        product_price = product_price[0]

        product_code = hxs.select('//input[@name="product"]/@value').extract()[0]
        image_url = hxs.select('//div[@class="product-img-box"]/div/div/ul/li/@data-large').extract()
        if not image_url:
            image_url = hxs.select('//div[@class="product-img-box"]/div/img[@class="th"]/@src').extract()
            if not image_url:
                image_url = hxs.select('//div[@class="product-img-box"]/div/div/img/@src').extract()

        image_url = image_url[0] if image_url else ''

        brand = hxs.select('//a[@itemprop="brand"]/text()').extract()
        brand = brand[0] if brand else ''

        categories = hxs.select('//div[contains(@class,"breadcrumb")]/ul/li//span[@itemprop="title"]/text()').extract()
        categories = [cat.strip() for cat in categories if not cat == 'Home'][:-1]

        product_price = extract_price(product_price)

        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            prices = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))

            prices_config = re.search(r'"spPrices":(.*),"spImages"', response.body)
            prices = json.loads(prices_config.group(1))

            product_price = extract_price(product_data['basePrice'])
            for option_identifier, option_name in products.iteritems():
                loader = ProductLoader(response=response, item=Product())

                loader.add_value("identifier", product_code + '-' + option_identifier)
                loader.add_value('name', product_name + option_name)
                loader.add_value('image_url', image_url)
                loader.add_value('price', extract_price(prices[option_identifier]))
                loader.add_value('url', response.url)
                loader.add_value('brand', brand)
                loader.add_value('sku', product_code)
                for category in categories:
                    loader.add_value('category', category)
                if not product_price:
                    loader.add_value('stock', 0)
                product = loader.load_item()
                yield product
        else:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', product_name)
            loader.add_value('url', response.url)
            loader.add_value('sku', product_code)
            loader.add_value('identifier', product_code)
            loader.add_value('brand', brand)
            loader.add_value('image_url', image_url)
            for category in categories:
                loader.add_value('category', category)
            loader.add_value('price', product_price)
            if not product_price:
                loader.add_value('stock', 0)

            yield loader.load_item()

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

class Force4Spider(BaseSpider):
    name = 'fmg_ mailspeed_marine-force4.co.uk'
    allowed_domains = ['force4.co.uk']

    start_urls = ['http://www.force4.co.uk/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//li[(contains(@class, "level2") and not(ul))or contains(@class, "level3")]//a/@href').extract()
        for category in categories:
            yield Request(category+'?limit=all', callback=self.parse_categories)    

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@class="breadcrumbs"]/ul/li//text()').extract()
        if categories:
            categories = filter(None, map(lambda x: x.strip() if x.strip()!='>' else '', categories))[2:]

        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'categories': categories})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        associated_products = hxs.select('//div[@class="associates"]//a/@href').extract()
        if associated_products:
            for associated_product in associated_products:
                yield Request(urljoin_rfc(base_url, associated_product), callback=self.parse_product)
            return

        loader = ProductLoader(item=Product(), response=response)
        product_name = hxs.select('//div[@class="product-name"]/h1/text()')[0].extract()
        product_price = hxs.select('//div[@class="product-shop-box"]/div[@class="price-box"]/p[@class="special-price"]/span[@class="price"]/text()').extract()
        if not product_price:
            product_price = hxs.select('//div[@class="product-shop-box"]/div[@class="price-box"]/span[@class="regular-price"]/span[@class="price"]/text()').extract()
        if product_price:
            product_price = product_price[0]
        product_code = hxs.select('//div[@class="product-code"]/text()').re('Product code: (.*)')[0]
        image_url = hxs.select('//img[@class="product-img-img"]/@src').extract()
        brand = hxs.select('//div[@class="product-name"]/span/text()').extract()
        brand = brand[0] if brand else ''
        categories = hxs.select('//div[@class="breadcrumbs"]/ul/li/a[text()!="Home" and text()!="Department"]/text()').extract()
        if not categories:
            categories = response.meta.get('categories', [])
        
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
                        prices[product] = prices.get(product, 0) +  extract_price(option['price'])


            for option_identifier, option_name in products.iteritems():
                loader = ProductLoader(response=response, item=Product())

                loader.add_value("identifier", product_code + '-' + option_identifier)
                loader.add_value('name', product_name + option_name)
                if image_url:
                    loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                loader.add_value('price', product_data['childProducts'][option_identifier]['finalPrice'])
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
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            for category in categories:
                loader.add_value('category', category)
            loader.add_value('price', product_price)
            if not product_price:
                loader.add_value('stock', 0)

            yield loader.load_item()

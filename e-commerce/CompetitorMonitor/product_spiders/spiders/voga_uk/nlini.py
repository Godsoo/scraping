import re
import csv
from StringIO import StringIO
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy import log

from phantomjs import PhantomJS

from datetime import datetime, timedelta


from utils import extract_price

class InteriorAddictSpider(BaseSpider):
    name = 'voga_uk-nlini.com'
    allowed_domains = ['nlini.com']
    start_urls = ('http://nlini.com/en',)


    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//ul[@id="nav"]//li/a/@href').extract()
        for category in categories:
            yield Request(category)

        products = hxs.select('//h2[contains(@class, "product-name")]/a/@href').extract()
        for product in products:
            categories = hxs.select('//div[@class="breadcrumbs"]/ul//span//text()').extract()[1:]
            yield Request(product, callback=self.parse_product, meta={'categories': categories})

        next = hxs.select('//a[contains(@class, "next")]/@href').extract()
        if next:
            yield Request(next[0])

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        image_url = hxs.select('//img[@id="image"]/@src').extract()
        image_url = image_url[0] if image_url else ''

        sku = hxs.select('//div[@class="sku"]/text()').re('SKU No.(.*)')
        sku = sku[0] if sku else ''

        product_name = hxs.select('//div[@class="product-name"]/h1/text()').extract()[0]
        brand = hxs.select('//div[@class="product-name"]/h3/text()').re('Inspired by (.*)')
        brand = brand[0] if brand else ''

        product_config_reg = re.search('var spConfig = new Product.Config\((\{.*\})\);', response.body)

        if product_config_reg:
            product_data = json.loads(product_config_reg.group(1))

            product_code = product_data['productId']
            base_price = extract_price(product_data[u'basePrice'])

            products = {}
            prices = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))
                        prices[product] = prices.get(product, 0) +  extract_price(option['price'])

            collected_products = 0

            for option_identifier, option_name in products.iteritems():
                product_loader = ProductLoader(item=Product(), response=response)
                product_loader.add_value('identifier', product_code + '-' + option_identifier)
                product_loader.add_value('price', base_price + prices[option_identifier])
                product_loader.add_value('name', product_name + option_name)
                product_loader.add_value('brand', brand)
                product_loader.add_value('url', response.url)
                for category in response.meta['categories']:
                    product_loader.add_value('category', category)
                product_loader.add_value('image_url', image_url)
                product_loader.add_value('sku', sku)
                collected_products += 1

                item = product_loader.load_item()
                yield item

            if not collected_products:
                product_loader = ProductLoader(item=Product(), response=response)
                product_loader.add_value('name', product_name)
                product_loader.add_value('url', response.url)
                for category in response.meta['categories']:
                    product_loader.add_value('category', category)
                product_loader.add_value('image_url', image_url)
                product_loader.add_value('price', base_price)
                product_loader.add_value('brand', brand)
                product_loader.add_value('identifier', product_code)
                product_loader.add_value('sku', sku)
                yield product_loader.load_item()


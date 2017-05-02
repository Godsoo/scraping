from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from decimal import *
import re
import json


class CrucialbmxSpider(BaseSpider):
    name = 'crucialbmx'
    allowed_domains = ['crucialbmxshop.com']
    start_urls = ('http://www.crucialbmxshop.com/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #parse categories
        urls = hxs.select('//*[@id="nav"]/li/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_list)

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #pagination
        urls = hxs.select('//div[@class="pages"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_list)
        category_name = hxs.select('//div[@class="page-title category-title"]/h1/text()').extract()
        if category_name:
            category_name = category_name[0]
        else:
            category_name = ''
        #products
        urls = hxs.select('//div[@class="category-products"]//li/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), meta={'category_name': category_name}, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        image_url = hxs.select('//p[@class="product-image"]/img[1]/@src').extract()
        category = response.meta.get('category_name')
        product_name = hxs.select('//div[@class="product-name"]/h1/text()').extract()[0]
        product_identifier = hxs.select('//input[@name="product"]/@value').extract()[0].strip()
        price = hxs.select('//*[@id="product-price-{}"]/span/text()'.format(product_identifier)).extract()
        if not price:
            price = hxs.select('//*[@id="product-price-{}"]/text()'.format(product_identifier)).extract()
        price = extract_price(price[0].strip())
        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))
            availability = product_data['salable']

            for identifier, option_name in products.iteritems():
                product_loader = ProductLoader(item=Product(), selector=hxs)
                product_loader.add_value('identifier', product_identifier + '_' + identifier)
                product_loader.add_value('name', product_name + option_name)
                if not availability[identifier]:
                    product_loader.add_value('stock', 0)
                if image_url:
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                product_loader.add_value('price', price)
                if price >= Decimal("50"):
                    product_loader.add_value('shipping_cost', 0)
                else:
                    product_loader.add_value('shipping_cost', 3.5)
                product_loader.add_value('url', response.url)
                product_loader.add_value('category', category)
                product = product_loader.load_item()
                yield product
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('name', product_name)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            product_loader.add_value('price', price)
            if price >= Decimal("50"):
                product_loader.add_value('shipping_cost', 0)
            else:
                product_loader.add_value('shipping_cost', 3.5)
            product_loader.add_value('url', response.url)
            product_loader.add_value('identifier', product_identifier)
            out_of_stock = hxs.select('//div[@class="add-to-box"]/p/text()').extract()
            if out_of_stock:
                if out_of_stock[0].strip() == 'Out of Stock':
                    product_loader.add_value('stock', 0)
            product_loader.add_value('category', category)
            product = product_loader.load_item()
            yield product
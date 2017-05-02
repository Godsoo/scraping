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

from heimkaupitems import HeimkaupProduct as Product

HERE = os.path.abspath(os.path.dirname(__file__))

class A4Spider(BaseSpider):
    name = 'heimkaup-a4.is'
    allowed_domains = ['a4.is']

    start_urls = ['http://a4.is/products']

    rotate_agent = True

    def __init__(self, *args, **kwargs):
        super(A4Spider, self).__init__(*args, **kwargs)

    def parse(self, response):
        base_url = get_base_url(response)
        
        categories = response.xpath('//div[@class="limit"]//a[contains(@href, "products")]/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

        next_pages = response.xpath('//div[@class="limit"]//a[contains(@href, "products") and not(contains(@href, "?page"))]/@href').extract()
        for next_page in next_pages:
            yield Request(urljoin_rfc(base_url, next_page))

        products = response.xpath('//a[contains(@class, "item")]/@href').extract()
        for url in set(products):
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        product_name = response.xpath('//h1[@class="product__title"]/text()').extract()[0].strip()
        brand = re.search('Trademark=(.*)', response.body)
        brand = brand.group(1) if brand else ''
        sku = response.xpath('//div[@class="product__vnr"]/text()').re('VNR: (.*)')
        product_price = response.xpath('//div[@class="product__price"]/text()').extract()
        if not product_price:
            product_price = ['0.00']
        product_price = product_price[0]
        product_code = response.xpath('//input[@name="productId"]/@value').extract()[0]
        image_url = response.xpath('//img[@class="img-responsive"]/@src').extract()
        category = response.xpath('//ol[@class="breadcrumbs"]//a/text()').extract()
        category = category[-1] if category else ''
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', product_name)
        loader.add_value('url', response.url)
        loader.add_value('sku', sku)
        loader.add_value('identifier', product_code)
        if image_url:
            loader.add_value('image_url', 'http:' + image_url[0])
        loader.add_value('category', category)
        product_price = extract_price(product_price.replace('.', '').replace(',', '.'))
        loader.add_value('price', product_price)
        yield loader.load_item()


    def parse_stock(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = response.meta.get('loader')
        stock = hxs.select('//div[@class="productonlager"]/text()').extract()
        if stock and stock[0] != u'1':
            loader.add_value('stock', 0)

        yield loader.load_item()

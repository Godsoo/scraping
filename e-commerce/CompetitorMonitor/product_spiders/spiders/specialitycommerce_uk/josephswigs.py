import os
import re
import json
import csv
import urlparse

from copy import deepcopy
from decimal import Decimal

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter

from scrapy import log

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class JosephsWigsSpider(BaseSpider):
    name = 'specialitycommerceuk-josephs-wigs.com'
    allowed_domains = ['josephs-wigs.com']

    start_urls = ['http://www.josephs-wigs.com']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//nav[@id="main-menu"]//a/@href').extract()
        for category in categories:
            url = urljoin_rfc(base_url, category)
            url = add_or_replace_parameter(url, 'limit', 'all')
            yield Request(url, callback=self.parse_products)    

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//a[@class="product-link"]/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        next_page = hxs.select('//a[@class="next i-next"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), callback=self.parse_products)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        brand = hxs.select('//span[@class="brand"]/a/img/@alt').extract()
        brand = brand[0] if brand else ''

        product_name = hxs.select('//div[@class="product_rht"]/h2/text()').extract()
        product_name = product_name[0].strip()
       
        product_price = hxs.select('//div[@class="product"]//span[@class="price-including-tax"]/span[@class="price"]/text()').extract()
        product_price = extract_price(product_price[0]) if product_price else 0
       
        product_code = hxs.select('//input[@name="product"]/@value').extract()[0]

        image_url = hxs.select('//div[@class="product"]//a[@class="thumb-link"]/img/@src').extract()
        image_url = image_url[0] if image_url else ''
        
        categories = hxs.select('//div[@class="breadcrumbs"]/ul/li/a/text()')[1:].extract()
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', product_name)
        loader.add_value('url', response.url)
        loader.add_value('sku', product_code)
        loader.add_value('identifier', product_code)
        loader.add_value('brand', brand)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url))
        loader.add_value('category', categories)
        loader.add_value('price', product_price)
        stock = hxs.select('//div[@class="product"]//button[@class="button btn-add btn-cart"]')
        if not stock:
            loader.add_value('stock', 0)

        item = loader.load_item()
        options = hxs.select('//script[contains(text(),"spConfig =")]').re('\.Config\((.*)\);')
        if options:
            options = json.loads(options[0])['attributes'].values()[0]['options']
            for option in options:
                item_option = deepcopy(item)
                option_identifier = option['id']
                item_option['identifier'] = item_option['identifier'] + '-' + option_identifier
                option_name = option['label']
                item_option['name'] = item_option['name'] + ' ' + option_name
                item_option['sku'] = item_option['identifier']
                if item_option['price']:
                    item_option['price'] += Decimal(option['price'])
                else:
                    item_option['price'] = Decimal(option['price'])
                if item_option['price'] < 100:
                    item_option['shipping_cost'] = 6.95
                yield item_option
        else:
            if item['price'] < 100:
                item['shipping_cost'] = 6.95
            yield item

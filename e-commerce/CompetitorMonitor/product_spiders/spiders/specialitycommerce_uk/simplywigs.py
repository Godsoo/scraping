import os
import re
import json
import csv
import urlparse

from copy import deepcopy

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class SimplyWigsSpider(BaseSpider):
    name = 'specialitycommerceuk-simplywigs.co.uk'
    allowed_domains = ['simplywigs.co.uk']

    start_urls = ['http://www.simplywigs.co.uk/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[@id="catalogue_nav"]/li/a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_products)    

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[contains(@class, "displayed_item")]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        pages = hxs.select('//a[@class="paging_button"]/@href').extract()
        for page in pages:
            yield Request(urljoin_rfc(base_url, page), callback=self.parse_products)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        brand = ''

        product_name = hxs.select('//div[@id="content"]/h1[@id="item-title"]/text()').extract()
        product_name = product_name[0].strip()
       
        product_price = hxs.select('//p[@id="item_price"]/strong/text()').extract()
        product_price = extract_price(product_price[0])
       
        product_code = hxs.select('//div[@id="table-add_to_basket"]//input[@name="iID"]/@value').extract()[0]

        image_url = hxs.select('//td[@id="default_image"]/a/img[@class="list_item-image"]/@src').extract()
        image_url = image_url[0] if image_url else ''
        
        categories = hxs.select('//p[@id="crumb_navigation"]/a/text()').extract()
        if categories:
            categories = categories[1:]
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', product_name)
        loader.add_value('url', response.url)
        loader.add_value('sku', product_code)
        loader.add_value('identifier', product_code)
        loader.add_value('brand', brand)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url))
        for category in categories:
            loader.add_value('category', category)
        loader.add_value('price', product_price)

        item = loader.load_item()
        options = hxs.select('//select[@class="item_option_dropdown"]/option')
        if options:
            for option in options:
                item_option = deepcopy(item)
                option_identifier = option.select('@value').extract()[0]
                item_option['identifier'] = item_option['identifier'] + '-' + option_identifier
                option_name = option.select('text()').extract()[0]
                item_option['name'] = item_option['name'] + ' ' + option_name
                yield item_option
        else:
            options = hxs.select('//input[contains(@id, "item_option_option")]')
            if options:
                for option in options:
                    item_option = deepcopy(item)
                    option_identifier = option.select('@value').extract()[0]
                    item_option['identifier'] = item_option['identifier'] + '-' + option_identifier
                    option_name = hxs.select('//label[contains(@id, "'+option_identifier+'")]/text()').extract()[0].strip()
                    item_option['name'] = item_option['name'] + ' ' + option_name
                    image_url = option.select('@image').extract()
                    if image_url:
                        item_option['image_url'] = urljoin_rfc(base_url, image_url[0].split('|')[0])
                    yield item_option
            else:
                yield item

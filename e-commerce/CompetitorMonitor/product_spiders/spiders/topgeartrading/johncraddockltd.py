import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
import hashlib

import csv
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from scrapy import log
from scrapy.shell import inspect_response
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from urlparse import urljoin

HERE = os.path.abspath(os.path.dirname(__file__))

class JohncraddockltdSpider(BaseSpider):
    name = 'johncraddockltd.co.uk'
    allowed_domains = ['johncraddockltd.co.uk']
    start_urls = ['http://www.johncraddockltd.co.uk/tyres/?startpos=0']
    minor_categories = ['All Terrain', 'Extreme Mud Terrain', 'General Tyres', 'Mud Terrain', 'Off Road Bias All Terrain', 'Road', 'Road Bias All Terrain']
    ids_seen = set()
    categories = {}
    done = False

    def __init__(self, *args, **kwargs):
        super(JohncraddockltdSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[contains(@class, "subcategories_list")]/ul/li')
        for item in categories:
            name = item.select('./a//text()').extract()
            url = item.select('./a/@href').extract()
            if name and url:
                url = urljoin(response.url, url.pop())
                name = name.pop()
                if name not in self.minor_categories:
                    yield Request(url, callback=self.parse_products_list, meta={'prior': 10, 'brand': name}, priority=10)
                else:
                    self.categories[name] = url
        self.parse_products_list(response)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        brand = response.meta.get('brand', '')
        category = response.meta.get('category', '')

        for link in hxs.select('//div[@class="category_grid"]/ul/li/ul/li[@class="description"]/div/div/a/@href').extract():
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_product, meta={'brand': brand, 'category': category})

        next_page = hxs.select('//li[@class="last"]/a/@href').extract()
        if next_page:
            url = urljoin(response.url, next_page.pop())
            yield Request(url, callback=self.parse_products_list, meta={'brand': brand, 'category': category})

    def spider_idle(self, spider):
        if self.categories:
            cats = self.categories.items()
            for name, url in cats:
                request = Request(url, dont_filter=True, meta={'category': name}, callback=self.parse_products_list)
                self._crawler.engine.crawl(request, self)
                self.categories.pop(name)
        elif not self.done:
            request = Request(self.start_urls[0], dont_filter=True, callback=self.parse_products_list)
            self._crawler.engine.crawl(request, self)
            self.done = True

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        brand = response.meta.get('brand', '')
        category = response.meta.get('category', '')
        sku = hxs.select('//input[@name="product_sku"]/@value').extract().pop()
        identifier = sku

        name = hxs.select('//h1[@class="gf_1"]/text()').extract()
        price = hxs.select('//span[@itemprop="price"]/text()').extract().pop()
        price = extract_price(price)
        # VAT
        price_vat = extract_price(str(float(price)*1.2))
        #image_url
        image_url = hxs.select('//img[@id="main_image"]/@src').extract()
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        if image_url:
            loader.add_value('image_url', urljoin(response.url, image_url.pop()))
        if brand:
            loader.add_value('brand', brand)
        if category or brand:
            loader.add_value('category', category or brand)
        loader.add_value('name', name)
        loader.add_value('price', price_vat)
        if price < 50.00:
            loader.add_value('shipping_cost', '5.00')
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier)
        #Stock
        #loader.add_value('stock', stock[0].strip())
        if sku not in self.ids_seen:
            self.ids_seen.add(sku)
            yield loader.load_item()


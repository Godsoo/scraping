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

from urlparse import urljoin

HERE = os.path.abspath(os.path.dirname(__file__))


class McidiventiSpider(BaseSpider):
    name = 'mcidiventi.co.uk'
    allowed_domains = ['mcidiventi.co.uk']
    start_urls = ['http://shop.mcidiventi.co.uk']
    brands = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        self.brands = hxs.select('//div[contains(@class,"menu-manufacturers")]/div[2]/ul/li/a/text()').extract()

        categories = hxs.select('//div[contains(@class,"menu-manufacturers")]/div[2]/ul/li/a/@href').extract()
        categories += hxs.select('//div[contains(@class,"menu-categories-list")]/div[2]/ul/li/a/@href').extract()

        for url in map(lambda url: urljoin_rfc(base_url, url), categories):
            yield Request(url, callback=self.parse_products_list)


    def parse_products_list(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        subcats = hxs.select('//div[@id="center-main"]/a/@href').extract()
        for subcat in subcats:
            yield Request(urljoin_rfc(base_url, subcat), callback=self.parse_products_list)

        if not subcats:
            products = hxs.select('//div[@class="products products-list"]/div/div/a[1]/@href').extract()
            for product in products:
                yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

            next_page = hxs.select('//a[img/@alt="Next page"]/@href').extract()
            if next_page:
                yield Request(urljoin_rfc(base_url, next_page[0]), callback=self.parse_products_list)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        tmp = hxs.select('//td[@id="product_code"]/text()').extract()
        loader.add_value('identifier', tmp[0])
        loader.add_value('sku', tmp[0])
        # loader.add_value('name', hxs.select('//td[@class="descr"]/text()').extract()[0].strip())
        name = hxs.select('//div[@id="center-main"]/h1/text()').extract()
        if not name:
            name = hxs.select('//form//td[@class="descr"]/text()').extract()

        loader.add_value('name', name[0].strip())
        # price
        price = hxs.select('//span[@id="product_price"]/text()').extract()
        if price:
            price = extract_price(price[0].strip())
            loader.add_value('price', price)
        # image_url
        image_url = hxs.select('//img[@id="product_thumbnail"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        # get brand
        tmp = hxs.select('//div[@id="center-main"]/h1/text()').extract()
        if tmp:
            if not self.brands:
                self.brands = hxs.select('//div[contains(@class,"menu-manufacturers")]/div[2]/ul/li/a/text()').extract()
            for brand in self.brands:
                if brand in tmp[0]:
                    loader.add_value('brand', brand)
                    break
        # category
        tmp = hxs.select('//div[@id="location"]/a[2]/text()').extract()
        if tmp:
            loader.add_value('category', tmp[0])
        # shipping_cost
        loader.add_value('shipping_cost', '15.00')
        # stock
        tmp = hxs.select('//ul[@class="simple-list"]//span[text()="Add to cart"]')
        if tmp:
            loader.add_value('stock', 1)
        yield loader.load_item()

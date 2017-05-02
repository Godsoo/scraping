# -*- coding: utf-8 -*-
import os
import urlparse
import re
import hashlib
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price_eu


HERE = os.path.abspath(os.path.dirname(__file__))


class FotozakupySpider(BaseSpider):

    name = 'fotozakupy'
    allowed_domains = ['fotozakupy.pl']
    start_urls = ['http://fotozakupy.pl/']


    def parse(self, response):

        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//ul[contains(@class, "nav-pills")]/li/a/@href').extract()
        for category in categories:
            yield Request(urlparse.urljoin(response.url, category), callback=self.parse_category)


    def parse_category(self, response):

        hxs = HtmlXPathSelector(response)
        subcats = hxs.select('//div[contains(@class, "col-sm-4")]/a[@class="middlemenu"]/@href').extract()
        subcats += hxs.select('//a[contains(@class, "middlemenu")]/@href').extract()
        for subcat in subcats:
            yield Request(urlparse.urljoin(response.url, subcat), callback=self.parse_subcat)


    def parse_subcat(self, response):

        hxs = HtmlXPathSelector(response)
        products = hxs.select('//h3[@class="producth3alt"]/strong/a/@href').extract()
        for product_url in products:
            yield Request(urlparse.urljoin(get_base_url(response), product_url), callback=self.parse_product)

        try:
            next_page = hxs.select(u'//ul[@class="pagination"]//a[contains(text(),"\xbb")]/@href').extract()[0]
            yield Request(urlparse.urljoin(get_base_url(response), next_page), callback=self.parse_subcat)
        except:
            pass


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        # Options
        options = hxs.select('//h3[contains(text(), "Warianty produktu")]/..//h2[@class="producttitlesimple"]/a/@href').extract()
        for url in options:
            yield Request(urlparse.urljoin(get_base_url(response), url), callback=self.parse_product)

        loader = ProductLoader(item=Product(), response=response)

        price = ''.join(hxs.select('//span[@itemprop="price"]/text()').extract()).replace(' ', '')
        price = extract_price_eu(price)

        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[contains(@class, "productbittitle")]/text()')

        if hxs.select('//div[@class="clearfix hidden-xs"]/a[@class="avail"]'):
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')
        categories = hxs.select('//ol[contains(@class, "breadcrumb")]/a/@title').extract()[1:-1]
        loader.add_value('category', categories)
        loader.add_xpath('brand', '//meta[@itemprop="brand"]/@content')
        if price < Decimal(1000):
            shipping_cost = '15'
        else:
            shipping_cost = '0'
        loader.add_value('shipping_cost', shipping_cost)
        sku = ''.join(hxs.select('//p[@class="productcode"]/strong/text()').extract())
        if not sku:
            sku = re.findall(re.compile("\/(\d*.)$"), response.url)
            sku = sku[0] if sku else ''
        loader.add_value('sku', sku.strip())
        loader.add_value('identifier', response.url.split("/")[-1])
        loader.add_xpath('image_url', "//div[@id='main-photo']//img/@src")
        yield loader.load_item()

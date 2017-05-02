# -*- coding: utf-8 -*-
import re

from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from product_spiders.utils import extract_price_eu as extract_price


class PixmaniaSpider(BaseSpider):
    name = 'eservices-it-pixmania.it'
    allowed_domains = ['pixmania.it']
    start_urls = ('http://www.pixmania.it/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//nav[@id="nav"]/ul/li[not(contains(a/h2//text(), "Videogiochi") or contains(a/h2//text(), "Casa"))]/ul/li/a/@href').extract()

        for url in categories:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        sub_categories = hxs.select('//section[@class="bsp"]/nav/ul/li/a/@href').extract()
        sub_categories += hxs.select('//nav[p[contains(text(), "Categoria")]]/ul/li/a/@href').extract()
        for sub_cat in sub_categories:
            yield Request(urljoin_rfc(base_url, sub_cat), callback=self.parse_category)

        products = hxs.select('//form//div[contains(@class, "resultList")]/article'
                              '//*[contains(@class, "productTitle")]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        next = hxs.select('//a[@class="next"]/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]), dont_filter=True, callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta

        products = hxs.select('//form//div[contains(@class, "resultList")]/article'
                              '//*[contains(@class, "productTitle")]/a/@href').extract()
        if products:
            for x in self.parse(response):
                yield x
            return

        base_url = get_base_url(response)

        price = hxs.select('//div[@class="row"]//span[@class="currentPrice"]/ins[@itemprop="price"]/text()').extract()
        if not price:
            price = "0.0"
        else:
            price = price.pop()

        identifier = response.url.split('/')[-1].split('-')[0]

        try:
            main_name = hxs.select('//span[@itemprop="name"]/text()').extract()[0].strip()
        except:
            main_name = ''
        try:
            brand = hxs.select('//span[@itemprop="brand"]/text()').extract()[0].strip()
        except:
            brand = ''

        product_name = brand + ' ' + main_name
        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()

        stock = hxs.select('//div[contains(@class, "availability")]/div/strong[contains(@class, "available")]/i[@class="icon-ok"]')

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', product_name)
        loader.add_value('url', response.url)
        loader.add_value('brand', brand)
        loader.add_value('price', extract_price(price))
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('image_url', image_url)
        categories = hxs.select('//div[@class="breadcrumb"]/ul/li/a/span/text()').extract()[1:]
        for category in categories:
            loader.add_value('category', category.encode(response.encoding))
        if not stock:
            loader.add_value('stock', 0)
        shipping_cost = hxs.select('//div/strong[@class="weee"]/text()').extract()
        if shipping_cost:
            shipping_cost = extract_price(shipping_cost[0])
            loader.add_value('shipping_cost', shipping_cost)
        yield loader.load_item()

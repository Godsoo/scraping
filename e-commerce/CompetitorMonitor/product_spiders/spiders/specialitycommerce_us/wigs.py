# -*- coding: utf-8 -*-
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin, urlsplit, urlunsplit
from product_spiders.utils import extract_price2uk, fix_spaces
import json
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class Wigs(BaseSpider):
    name = "wigs.com"
    allowed_domains = ["wigs.com"]
    start_urls = ["http://www.wigs.com/"]

    map_deviation_detection = True

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        category_urls = hxs.select('//ul[contains(@class, "level0")]//div[@class="sub-nav-col"]//dd/a/@href').extract()
        for url in category_urls:
            yield Request(urljoin(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        next_url = hxs.select('//div[@class="pager"]//a[@title="Next"]/@href').extract()
        if next_url:
            yield Request(urljoin(base_url, next_url[0]), callback=self.parse_category)
        product_urls = hxs.select('//div[@class="category-view"]//h2[@itemprop="name"]/a/@href').extract()
        for url in product_urls:
            yield Request(urljoin(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(selector=hxs, item=Product())

        product_id = hxs.select('//input[@name="product"]/@value').extract()[0]
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        name = hxs.select('//h1[@itemprop="name"]/span[@class="fn"]/text()').extract()[0]
        loader.add_xpath('name', '//h1[@itemprop="name"]/span[@class="fn"]/text()')
        brand = hxs.select('//h1[@itemprop="name"]/span[@class="brand"]/text()').extract()
        brand = brand[0][3:]
        loader.add_value('brand', brand)
        sku = hxs.select('//li[contains(text(), "SKU:")]/text()').extract()[0][5:]
        loader.add_value('sku', sku)
        loader.add_xpath('category', '//li[contains(@class, "category")]/a/text()')
        loader.add_xpath('image_url', '//img[@itemprop="image"]/@src')
        stock = 0
        price = 0
        price = hxs.select('//div[contains(@class,"product-main-info")]//span[@itemprop="price"]/text()').extract()
        if price:
            price = price[0]
            stock = 1
        else:
            price = hxs.select('//div[contains(@class,"product-main-info")]//span[@class="price"]/text()').extract()
            if price:
                price = price[0]
                stock = 1
        loader.add_value('stock', stock)
        loader.add_value('price', price)
        price = loader.get_output_value('price')
        if price and Decimal(price) < 50.0:
            loader.add_value('shipping_cost', '7.95')
        loader.add_value('url', response.url)
        product = loader.load_item()
        options = hxs.select('//div[@class="color-item"]')
        if not options:
            yield product
            return
        for option in options:

            option_name = option.select('./p[2]/text()').extract()
            if option_name:
                product['name'] = ' '.join((name, option_name[0]))
            product['identifier'] = product_id + option.select('./p[2]/@id').extract()[0]
            product['image_url'] = option.select('./p[1]/img/@src').extract()[0]
            yield product

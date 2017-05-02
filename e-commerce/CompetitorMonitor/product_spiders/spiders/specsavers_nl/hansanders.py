# -*- coding: utf-8 -*-
"""
Customer: Specsavers NL
Website: https://www.hansanders.nl/lens/
Extract all products on site. Do not extract these options http://screencast.com/t/g8toaiUYy

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4760-specsavers-nl-|-hansanders-|-new-site/details#

"""

import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter
from urlparse import urljoin

from product_spiders.utils import extract_price_eu

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader



class HansAnders(BaseSpider):
    name = "specsavers_nl-hansanders.nl"
    allowed_domains = ["hansanders.nl"]
    start_urls = ['https://www.hansanders.nl/lens/', 'https://www.hansanders.nl/lenzen/']

    def parse(self, response):
        base_url = get_base_url(response)

        categories = response.xpath('//section[contains(@class, "module--product-tabs")]//a/@href').extract()
        categories += response.xpath('//li[@class="category__item"]/a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))

        products = response.xpath('//p[@class="product__title"]/a/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product)

        next = response.xpath('//li[contains(@class, "pagination--next")]/a/@href').extract()
        if next:
            yield Request(response.urljoin(next[0]))

    def parse_product(self, response):
        base_url = get_base_url(response)

        name = response.xpath('//div[@class="column--info"]/h1/text()').extract()[0].strip()

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name)
        price = response.xpath('//p[@class="price__total"]/text()').extract()[0].strip()
        #price = response.xpath('//meta[@itemprop="price"]/@content').extract()[0]
        loader.add_value('price', extract_price_eu(price))
        image_url = response.xpath('//div[@class="holder--visual"]/img/@src').extract()
        if not image_url:
            image_url = response.xpath('//div[@class="item"]/a/img/@src').extract()

        if image_url:
            loader.add_value('image_url', image_url[0])
        categories = response.xpath('//div[@class="breadcrumbs--path"]/a/span/text()').extract()[1:]
        brand = response.xpath('//tr[@class="specs__item" and td[contains(text(), "Merk")]]/td[not(contains(text(), "Merk")) and not(svg)]/text()').extract()
        brand = brand[0].strip() if brand else ''
        loader.add_value('brand', brand)
        loader.add_value('category', categories)
        loader.add_value('url', response.url)
        identifier = response.xpath('//div[@id="page--product"]/@data-id').extract()[0]
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)

        yield loader.load_item()

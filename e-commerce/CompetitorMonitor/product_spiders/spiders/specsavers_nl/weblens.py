# -*- coding: utf-8 -*-
"""
Customer: Specsavers NL
Website: http://weblens.nl
Extract all products. Do not extract these options http://screencast.com/t/ieMLKk52K

Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5108

"""

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter
from urlparse import urljoin

from product_spiders.utils import extract_price_eu as extract_price

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class Weblens(BaseSpider):
    name = "specsavers_nl-weblens.nl"
    allowed_domains = ["weblens.nl"]
    start_urls = ['http://weblens.nl/']

    def parse(self, response):
        base_url = get_base_url(response)

        categories = response.xpath('//nav[@role="navigation"]//li/a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url))

        products = response.xpath('//div[@class="item"]/a/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)

        name = response.xpath('//div[@id="product_info"]/h1/text()').extract()[0]

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name.strip())
        price = response.xpath('//span[@class="product_price_cost_total"]/text()').extract()
        price = extract_price(price[0]) if price else 0
        loader.add_value('price', price)
        image_url = response.xpath('//img[@id="product_image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url[0]))
        loader.add_value('brand', '')
        category = response.xpath('//span[@class="breadcrumbsItem"]//text()').extract()
        if category:
            loader.add_value('category', category)
        loader.add_value('url', response.url)
        identifier = response.xpath('//input[@name="pid"]/@value').extract()[0]
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)

        yield loader.load_item()

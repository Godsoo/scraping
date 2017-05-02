# -*- coding: utf-8 -*-
"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4551
"""
import re
import json
from urlparse import urljoin

from scrapy import Spider, Request
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.utils.url import url_query_parameter

from product_spiders.items import ProductLoaderWithNameStrip as ProductLoader, Product


class LenstoreSpider(Spider):
    name = 'specsavers_uk-lenstore.co.uk'
    allowed_domains = ('lenstore.co.uk', )
    start_urls = ['http://www.lenstore.co.uk']

    def parse(self, response):
        urls = response.xpath('//div[@id="Information"]//a/@href').extract()
        for url in urls:
            yield Request(url, callback=self.parse_products)

    def parse_products(self, response):
        urls = response.xpath('//span[@class="prodTitle"]/../@href').extract()
        for url in urls:
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('identifier', '//meta[@itemprop="sku"]/@content')
        loader.add_xpath('name', '//span[@itemprop="name"]/text()')
        loader.add_xpath('sku', '//meta[@itemprop="sku"]/@content')

        loader.add_xpath('price', '//meta[@itemprop="price"]/@content')
        if not loader.get_output_value('price'):
            self.log('No price found for {}'.format(response.url))
            return

        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()[0]

        loader.add_value('image_url', urljoin(get_base_url(response), image_url))
        loader.add_xpath('brand', '//div[@itemprop="manufacturer"]/meta[@itemprop="name"]/@content')
        loader.add_value('url', response.url)
        loader.add_value('shipping_cost', '2.99')
        stock = response.xpath('//meta[@itemprop="availability"]/@content')
        if stock and stock.extract()[0] != 'InStock':
            loader.add_value('stock', 0)
        category = ''.join(response.xpath('//p[@itemprop="breadcrumb"]//text()').extract())
        category = category.split(u'\u203a')
        category = category[1:-1]
        for c in category:
            loader.add_value('category', c.strip())

        yield loader.load_item()


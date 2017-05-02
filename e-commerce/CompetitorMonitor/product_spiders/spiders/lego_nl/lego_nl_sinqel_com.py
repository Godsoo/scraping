"""
This spider was moved from the FMS system, because it had issues running there.
"""

import csv
import os
import json
import copy
import re
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, url_query_parameter
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStripEU as ProductLoader

from scrapy.shell import inspect_response

HERE = os.path.abspath(os.path.dirname(__file__))


class JetSpider(BaseSpider):
    name = 'lego_nl_sinqel_com'
    allowed_domains = ['sinqel.com']
    start_urls = ('http://www.sinqel.com/merken/lego/?sort=asc&limit=100',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_pages = hxs.select('//li[@class="number"]//a/@href|li[@class="next"]//a/@href').extract()
        for url in next_pages:
            yield Request(urljoin_rfc(base_url, url))

        for url in hxs.select('//div[@class="product-block-inner"]/div[@class="name"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), selector=hxs)
        sku = hxs.select('//span[@itemprop="sku"]/text()')[0].extract()
        loader.add_xpath('identifier', '//*[@itemprop="productID"]/@content')
        loader.add_xpath('name', '//div[@class="content"]/h4/text()')
        loader.add_value('brand', 'Lego')
        loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        price = ''.join(response.css('span.price ::text').extract())
        loader.add_value('price', price)
        if Decimal(loader.get_output_value('price')) < 50:
            loader.add_value('shipping_cost', Decimal('2.99'))

        image_url = response.css('.main-img ::attr(data-src)').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

        for category in hxs.select('//div[contains(@class,"breadcrumbs")]/a/text()')[1:].extract():
            loader.add_value('category', category)
        yield loader.load_item()

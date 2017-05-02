#!/usr/bin/python
# -*- coding: latin-1 -*-

import re
import logging

from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)


class PixmaniaSpider(BaseSpider):
    name = 'pixmania.com_tec7'
    allowed_domains = ['pixmania.co.uk']
    start_urls = ('http://www.pixmania.co.uk/',)

    URLS = {
        'http://www.pixmania.co.uk/cameras/digital-camera-1-m.html': 'Digital camera',
        'http://www.pixmania.co.uk/tv-video/television-8-m.html': 'Television'
    }

    def start_requests(self):
        for url, category in self.URLS.items():
            yield Request(url,
                          meta={'category': category})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        filters = hxs.select('//aside[@id="filters"]//li/a/@href').extract()

        for url in filters:
            yield Request(urljoin_rfc(base_url, url), meta=response.meta)

        products = hxs.select('//form//div[contains(@class, "resultList")]/article'
                              '//h2[contains(@class, "productTitle")]/a/@href').extract()

        for url in products:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product,
                          meta=response.meta)

        pages = hxs.select('//ul[@class="pagination"]//a/@href').extract()

        for url in pages:
            yield Request(urljoin_rfc(base_url, url), meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        category = response.meta.get('category')

        loader = ProductLoader(item=Product(), response=response)

        name = hxs.select('//span[@itemprop="name"]/text()').extract()[0].strip()
        brand = hxs.select('//span[@itemprop="brand"]/text()').extract()[0].strip()

        loader.add_value('name', brand + ' ' + name)
        loader.add_value('brand', brand)
        loader.add_xpath('price', '//ins[@itemprop="price"]/text()')
        loader.add_value('identifier', response.url.split('/')[-1].split('-')[0])
        loader.add_value('sku', response.url.split('/')[-1].split('-')[0])
        loader.add_value('category', category)
        loader.add_value('url', response.url)

        yield loader.load_item()

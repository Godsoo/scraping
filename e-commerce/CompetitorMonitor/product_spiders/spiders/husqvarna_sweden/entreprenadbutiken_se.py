# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)
from product_spiders.utils import extract_price_eu

from decimal import Decimal


class EntreprenadbutikenSpider(BaseSpider):
    name = u'entreprenadbutiken.se'
    allowed_domains = ['entreprenadbutiken.se']
    start_urls = [
        u'http://www.entreprenadbutiken.se/',
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select('//div[@id="leftField"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select('//div[@id="leftField"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

        for url in hxs.select('//a[@class="gridArticleName"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@class="articleName"]/text()')
        loader.add_xpath('identifier', '//input[@id="article-art" and @name="art"]/@value')
        loader.add_value('price', self._get_price(hxs))
        loader.add_value('category', hxs.select('//div[@class="breadcrumb"]/a/text()').extract()[1:])
        loader.add_xpath('sku', '//div[@id="articleNr"]/text()', re=r'Artikelnummer: (.*)')
        loader.add_xpath('image_url', '//a[@rel="article-image"]/img/@src')

        yield loader.load_item()

    def _get_price(self, hxs):
        price = ''.join(hxs.select('//td[@id="price"]//text()').re(r'[\d.,]+'))
        if price:
            return extract_price_eu(price)
        return Decimal('0.0')

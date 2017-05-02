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


class MaskinklippetSpider(BaseSpider):
    name = u'maskinklippet.se'
    allowed_domains = ['maskinklippet.se']
    start_urls = [
        u'http://www.maskinklippet.se/',
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select('//ul[@id="category-navigation"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select('//ul[@id="category-navigation"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

        for url in hxs.select('//div[@class="product-name"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        next = hxs.select('//a[contains(@class, "paging-link-next")]/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]), callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//*[@itemprop="name"]/text()')
        loader.add_xpath('identifier', '//*[@itemprop="name"]/@data-productid')
        loader.add_value('price', self._get_price(hxs))
        loader.add_xpath('category', '//ul[@id="category-navigation"]/li[contains(@class, "active")]/a/text()')
        loader.add_xpath('sku', '//*[@itemprop="description"]//td[contains(.//text(), "Modellnamn")]/following-sibling::td//text()')
        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
        loader.add_value('image_url', image_url)

        yield loader.load_item()

    def _get_price(self, hxs):
        price = hxs.select('//*[@itemprop="price"]/text()').extract()
        if price:
            return extract_price_eu(price[0])
        return Decimal('0.0')

# -*- coding: utf-8 -*-

"""
Name: applejack-totalbeverage.net
Account: Apple Jack
"""


import urllib

try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider

from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)


class TotalBeverageSpider(BaseSpider):
    name = 'applejack-totalbeverage.net'
    allowed_domains = ['totalbeverage.net']
    start_urls = ('http://totalbeverage.net/',)

    def parse(self, response):
        base_url = get_base_url(response)

        categories = response.xpath('//div[@id="nav"]//a/@href').extract()
        categories += response.xpath('//div[@id="category"]//li/a/@href').extract()
        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url)

        products = response.xpath('//div[contains(@class, "MainProducts")]/div[a]')
        for product_xs in products:
            loader = ProductLoader(item=Product(), selector=product_xs)
            loader.add_xpath('url', 'a/@href', lambda u: urljoin_rfc(base_url, u[0]))
            name = product_xs.xpath('.//p[@class="productName"]/a/text()').extract()[0].strip()
            product_size = product_xs.xpath('.//p[contains(@class, "size")]/text()').re(r'Size: (.*)')
            if product_size:
                name += u' ' + product_size[0].strip()

            price = product_xs.xpath('.//p[contains(@class, "price")]/text()').re(r'[\d,.]+')[0]

            loader.add_value('name', name)
            loader.add_value('price', price)

            categories = response.xpath('//ol[contains(@class, "breadcrumb")]/li/a/text()').extract()[1:]
            loader.add_value('category', categories)

            image_url = product_xs.xpath('.//div[@class="image-box"]/img/@src').extract()
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

            identifier = product_xs.xpath('.//button[@class="btn buyButton"]/@onclick').re(r'\d+')
            loader.add_value('identifier', identifier[0])
            loader.add_value('sku', identifier[0])

            yield loader.load_item()

        # pagination
        next_page = response.xpath(u'//a[@data-page="next" and contains(text(), "›")]/@href').extract()
        if next_page:
            next_page = urllib.unquote(next_page[0])
            yield Request(next_page)

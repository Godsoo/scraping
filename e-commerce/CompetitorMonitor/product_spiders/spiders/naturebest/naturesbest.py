import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
import hashlib

import csv

from product_spiders.items import Product, ProductLoaderWithNameStrip\
                             as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))


class NaturesBestSpider(BaseSpider):
    name = 'naturesbest.co.uk'
    allowed_domains = ['www.naturesbest.co.uk', 'naturesbest.co.uk']
    start_urls = ('http://www.naturesbest.co.uk/page/productdirectory/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in filter(lambda url: '/pharmacy/' not in url, hxs.select('//a[contains(@id, "prod_")]/@href').extract()):
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        name = hxs.select(u'//div[@class="productTITLE"]/h1/text()').extract()
        if name:
            url = response.url
            url = urljoin_rfc(get_base_url(response), url)
            skus = hxs.select('//input[@name="sku"]/@value').extract()
            options = hxs.select('//td[@class="skuname"]/label/text()').extract()
            prices = hxs.select('//td[@class="price"]/text()').extract()
            options_prices = zip(options, skus, prices)
            for option, sku, price in options_prices:
                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('url', url)
                loader.add_value('name', (name[0].strip() + ' ' + option.strip()).replace(u'\xa0', ' '))
                loader.add_value('identifier', sku)
                loader.add_value('sku', sku)
                loader.add_value('price', price)
                yield loader.load_item()

import re
import os
import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
import hashlib

from product_spiders.utils import extract_price

import csv

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class DavidsonsLiquorsSpider(BaseSpider):
    name = 'davidsonsliquors.com'
    allowed_domains = ['www.davidsonsliquors.com', 'davidsonsliquors.com']
    start_urls = ('https://www.davidsonsliquors.com',)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        # categories
        categories = hxs.select('//ul[@id="nav"]//a/@href').extract()
        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url)

        # products
        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for url in products:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product)

        # pagination
        next_page = re.findall("setNavigationUrl\(\'(.*)',", response.body)
        if next_page:
            next_page = urllib.unquote(next_page[0])
            yield Request(next_page)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(selector=hxs, item=Product())
        loader.add_value('url', response.url)
        name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0].strip()
        product_size = hxs.select('//div[strong[contains(text(), "Size: ")]]/text()').extract()[-1].strip()
        name += u' ' + product_size

        price = extract_price(''.join(''.join(hxs.select('//form//p[@class="special-price"]//span[@class="price"]/text()').extract()).split()))
        if not price:
            price = extract_price(''.join(''.join(hxs.select('//span[@class="regular-price"]//span[@class="price"]/text()').extract()).split()))

        loader.add_value('name', name)
        loader.add_value('price', price)

        categories = hxs.select('//div[@class="breadcrumbs"]/ul/li/a/span/text()').extract()[1:]
        loader.add_value('category', categories)

        loader.add_value('brand', '')

        image_url =  hxs.select('//img[@class="image-retina"]/@src').extract()
        loader.add_value('image_url', image_url[-1])

        identifier = hxs.select('//div[@class="product-sku"]/span/text()').extract()
        loader.add_value('identifier', identifier[0])
        yield loader.load_item()

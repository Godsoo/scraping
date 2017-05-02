# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
import re

from decimal import Decimal

from product_spiders.spiders.lego_cz.legobase import LegoMetadataBaseSpider


class SparkysSpider(LegoMetadataBaseSpider):
    name = u'sparkys.cz'
    allowed_domains = ['www.sparkys.cz']
    start_urls = [
        u'http://www.sparkys.cz/lego',
    ]
    errors = []
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        pages = hxs.select('//ul[@id="paging"]/li/a/@href').extract()
        items = hxs.select('//div[@class="product" or @class="product "]/h3/a/@href').extract()
        for url in items:
            yield Request(urljoin(base_url, url), callback=self.parse_product)
        for url in pages:
            yield Request(urljoin(base_url, url), callback=self.parse)

    def parse_price(self, price):
        try:
            price, count = re.subn(r'[^0-z .,]*([0-9 .,]+)\WK.*', r'\1', price.strip())
        except TypeError:
            return False
        if count:
            price = price.replace(",", "").replace(" ", "")
            try:
                price = float(price)
            except ValueError:
                return False
            else:
                return price
        return False

    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//*[@itemprop="name"]/text()').extract().pop().strip()

        # category = hxs.select('//div[@class="breadcrumbs"]/a/text()')[-1].extract().strip()
        # category = name.split('-')[0].strip()
        categories = map(unicode.strip, hxs.select('//ul[@id="breadcrumbs"]/li/a/text()').extract())
        if categories:
            category = categories[-1]
            if category.startswith(u"\xbb"):
                category = category[2:]
        else:
            category = ''

        pid = hxs.select('//*[@itemprop="identifier"]/text()').pop().extract().strip()

        sku = hxs.select(u'//th[contains(text(), "K\xf3d produktu")]/following-sibling::td[1]/text()').extract().pop().strip()

        price = hxs.select('//meta[@itemprop="price"]/@content').pop().extract()

        stock = hxs.select('//meta[@itemprop="availability" and @content="in_stock"]')

        if price:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('url', urljoin(base_url, response.url))
            loader.add_value('name', name)
            loader.add_xpath('image_url', '//img[@itemprop="image"]/@src', Compose(lambda v: urljoin(base_url, v[0])))
            loader.add_value('price', price)
            loader.add_value('category', category)
            loader.add_value('sku', sku)
            loader.add_value('identifier', pid)
            loader.add_value('brand', 'LEGO')
            if Decimal(price) < Decimal('3000'):
                loader.add_value('shipping_cost', 95)
            if not stock:
                loader.add_value('stock', 0)
            yield self.load_item_with_metadata(loader.load_item())
        else:
            self.errors.append("No price set for url: '%s'" % urljoin(base_url, response.url))

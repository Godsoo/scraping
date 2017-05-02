# -*- coding: utf-8 -*-

import urlparse
import os
import xlrd

from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))


class CalPhotoSpider(BaseSpider):
    name = 'wexphotographic_used-calphoto.co.uk'
    allowed_domains = ['calphoto.co.uk']
    start_urls = ['https://www.calphoto.co.uk/category/used']

    def parse(self, response):
        # products
        products = response.xpath('//ul[contains(@class, "ish-productList")]//a[contains(@class, "product-link")]/@href').extract()
        for product in products:
            yield Request(product, callback=self.parse_product)

        # products next page
        next_page = response.xpath('//li[contains(@class, "ish-pagination-list-next")]/a/@href').extract()
        if next_page:
            yield Request(next_page[0])

    def parse_product(self, response):
        url = response.url

        options = response.xpath('//a[contains(@id, "pickerItem")]/@href').extract()
        for option in options:
            option_url = urlparse.urljoin(get_base_url(response), option)
            yield Request(option, callback=self.parse_product)

        l = ProductLoader(item=Product(), response=response)

        name = response.xpath('//h1[@class="ish-productTitleLong"]/text()').extract()
        if not name:
            name = response.xpath('//h1[@class="ish-productTitle"]/text()').extract()

        if not name:
            name = response.xpath('//h1[@itemprop="name"]/text()').extract()

        if not name:
            return
        name = name[0].strip()
        l.add_value('name', name)


        price = response.xpath('//div[contains(@class, "finalPrice")]/span[@class="bigprice"]/text()').extract()
        price = price[0].split()[-1] if price else 0
        l.add_value('price', price)

        sku = response.xpath('//span[@itemprop="mpn"]/text()').extract()
        l.add_value('sku', sku)

        identifier = response.xpath('//span[@itemprop="sku"]/text()').extract()[0]
        l.add_value('identifier', identifier)
        categories = response.xpath('//ol[@class="ish-breadcrumbs-list"]/li/a/span/text()').extract()[-3:]
        l.add_value('category', categories)

        image_url = response.xpath('//img[@class="ish-product-image"]/@src').extract()[0]
        l.add_value('image_url',image_url)

        l.add_value('url', url)
        l.add_xpath('brand', '//span[@itemprop="brand"]/text()')
 
        out_of_stock = response.xpath("//link[@itemprop='availability' and contains(@href, 'OutOfStock')]")
        if out_of_stock:
            l.add_value('stock', 0)

        product = l.load_item()


        yield product
 

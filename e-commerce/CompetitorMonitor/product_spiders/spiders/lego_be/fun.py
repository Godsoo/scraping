# -*- coding: utf-8 -*-

import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.utils import extract_price_eu as extract_price

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class FunSpider(BaseSpider):
    name = "lego_be-fun.be"
    allowed_domains = ["fun.be"]
    start_urls = ["http://www.fun.be/play/lego-kopen/alle-lego.html"]

    _re_sku = re.compile('(\d\d\d\d\d?)')

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        next_url = hxs.select('//a[contains(@class, "next")]/@href').extract()
        if next_url:
            yield Request(urljoin(base_url, next_url[0]))

        product_urls = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for url in product_urls:
            yield Request(urljoin(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(selector=hxs, item=Product())

        name = hxs.select('//div[@class="product-name"]/span/text()').extract()[0].strip()
        loader.add_value('name', name)
        loader.add_value('url', response.url)

        price = hxs.select('//div[@class="buy-container"]//p[@class="special-price"]/span[@class="price"]/text()').extract()
        if not price:
            price = hxs.select('//div[@class="buy-container"]//span[@class="regular-price"]/span[@class="price"]/text()').extract()
        price = price[0] if price else 0

        loader.add_value('price', extract_price(price))

        img_url = hxs.select('//img[@id="image-0"]/@src').extract()
        if img_url:
            loader.add_value('image_url', urljoin(base_url, img_url[0]))

        loader.add_xpath('category', '//li[span/text()="Thema"]/span[@class="data"]/text()')
        loader.add_value('brand', 'Lego')

        identifier = hxs.select('//input[@name="product"]/@value').extract()
        if not identifier:
            log.msg('ERROR >>> Product without identifier: ' + response.url)
            return
        loader.add_value('identifier', identifier[0])

        loader.add_xpath('sku', '//li[span/text()="Artikelnummer"]/span[@class="data"]/text()')

        out_of_stock = hxs.select('//span[@class="out-of-stock-msg"]')
        if out_of_stock or loader.get_output_value('price')<=0:
            loader.add_value('stock', 0)

        if loader.get_output_value('price')<50:
            loader.add_value('shipping_cost', 2.99)
       
        yield loader.load_item()

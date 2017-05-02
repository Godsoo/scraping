# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
import re

from product_spiders.spiders.lego_cz.legobase import LegoMetadataBaseSpider


class LegacekSpider(LegoMetadataBaseSpider):
    name = u'legacek.cz'
    allowed_domains = ['www.legacek.cz']
    start_urls = [
        u'http://www.legacek.cz/search?controller=search&orderby=position&orderway=desc&search_query=LEGO',
    ]
    errors = []
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        next_page = hxs.select('//div[@id="pagination"]/span[@id="pagination_next"]/a/@href').extract()
        items = hxs.select('//div[@class="catalog"]/div/h2/a/@href').extract()
        for url in items:
            yield Request(urljoin(base_url, url), callback=self.parse_product)
        if next_page:
            yield Request(urljoin(base_url, next_page.pop()), callback=self.parse)

    def parse_price(self, price):
        try:
            price, count = re.subn(r'[^0-9 .,]*([0-9 .,]+)\WK.*', r'\1', price.strip())
        except TypeError:
            return False
        if count:
            price = price.replace(",", ".").replace(" ", "")
            try:
                price = float(price)
            except ValueError:
                return False
            else:
                return price
        elif price.isdigit():
            return float(price)
        return False

    def get_sku_from_text(self, text):
        try:
            id, count = re.subn(r'[^0-9]*([0-9]+).*', r'\1', text)
        except TypeError:
            return ""
        if count:
            id = id.strip()
            try:
                int(id)
            except ValueError:
                return ""
            else:
                return id
        return False

    def get_pid_from_url(self, text):
        try:
            id, count = re.subn(r'.*-([0-9]+)\.html.*', r'\1', text)
        except TypeError:
            return ""
        if count:
            id = id.strip()
            try:
                int(id)
            except ValueError:
                return ""
            else:
                return id
        return False

    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = "".join(map(lambda x: x.strip(), hxs.select('//div[@id="primary_block"]/h1/descendant-or-self::text()').extract()))
        if name.startswith("LEGOLAND"):
            return

        category = hxs.select('//div[@class="breadcrumb "]/a/text()').extract()
        if category:
            category = category.pop()
        else:
            category = ""

        pid = hxs.select('//input[@name="id_product"]/@value').extract()

        sku = hxs.select('//label[@for="product_reference"]/following-sibling::span[1]/text()').extract()
        if not sku:
            sku = pid
        elif sku[0].endswith("-lego"):
            sku = sku.pop()[0:-5]

        try:
            price = self.parse_price(hxs.select('//p[@class="our_price_display"]/strong/span/text()').pop().extract())
        except IndexError:
            return

        stock = hxs.select('//p[@id="pQuantityAvailable"]/span[@class="yes"]')

        if price:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('url', urljoin(base_url, response.url))
            loader.add_value('name', name)
            loader.add_xpath('image_url', '//div[@id="image-block"]/span/img/@src', Compose(lambda v: urljoin(base_url, v[0])))
            loader.add_value('price', price)
            loader.add_value('category', category)
            loader.add_value('sku', sku)
            loader.add_value('identifier', pid)
            loader.add_value('brand', 'LEGO')
            if not stock:
                loader.add_value('stock', 0)
            yield self.load_item_with_metadata(loader.load_item())
        else:
            self.errors.append("No price set for url: '%s'" % urljoin(base_url, response.url))

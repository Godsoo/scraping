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


class IhrackarstviSpider(LegoMetadataBaseSpider):
    name = u'i-hrackarstvi.cz'
    allowed_domains = ['www.i-hrackarstvi.cz']
    start_urls = [
        u'http://www.i-hrackarstvi.cz/lego/',
    ]
    errors = []
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        items = hxs.select('//a[@class="menu-item"]/@href').extract()
        for url in items:
            yield Request(urljoin(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        items = hxs.select('//a[@class="product-preview"]/@href').extract()
        next_page = hxs.select('//a[contains(@class, "next")]/@href').extract()
        for url in items:
            yield Request(urljoin(base_url, url), callback=self.parse_product)
        if next_page:
            yield Request(urljoin(base_url, next_page.pop()), callback=self.parse_category)

    def parse_price(self, price):
        try:
            price, count = re.subn(r'[^0-9 .,]*([0-9 .,]+)\W*K.*', r'\1', price.strip())
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

    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//h1[@class="active"]/text()').pop().extract().strip()

        category = hxs.select('//div[@class="common_template_breadcrumb"]/a/text()').pop().extract().strip()

        sku =  hxs.select(u'//tr[th/text()="Kód zboží:"]/td/text()').extract().pop().strip()
        if sku.endswith('LEG'):
            sku = sku[:-3]

        pid = hxs.select('//input[@id="detail_id"]/@value')
        pid = pid.pop().extract().strip() if pid else None
        if not pid:
            pid =  hxs.select('//a[@class="oblibene" and contains(@href, "createfav")]/@href').extract()[0].split('createfav=')[-1]

        price = self.parse_price(hxs.select('//span[@class="castka"]/text()').extract()[0])

        stock = hxs.select('//div[@class="dostupnost" and contains(text(), "Skladem")]')

        if price:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('url', urljoin(base_url, response.url))
            loader.add_value('name', name)
            try:
                loader.add_xpath('image_url', '//div[@class="hlavni-obrazek"]/a/img/@src', Compose(lambda v: urljoin(base_url, v[0])))
            except IndexError:
                self.errors.append("No image set for url: '%s'" % urljoin(base_url, response.url))
            loader.add_value('price', price)
            loader.add_value('category', category)
            loader.add_value('sku', sku)
            loader.add_value('identifier', pid)
            loader.add_value('brand', 'LEGO')
            if int(price) < 300:
                loader.add_value('shipping_cost', 70)
            if not stock:
                loader.add_value('stock', 0)
            yield self.load_item_with_metadata(loader.load_item())
        else:
            self.errors.append("No price set for url: '%s'" % urljoin(base_url, response.url))

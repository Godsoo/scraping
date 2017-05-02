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


class HrackynejlevnejiSpider(LegoMetadataBaseSpider):
    name = u'hrackynejlevneji.cz'
    allowed_domains = ['www.hrackynejlevneji.cz']
    start_urls = [
        u'http://www.hrackynejlevneji.cz/index.php?route=product/search&search=Lego',
    ]
    errors = []
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        next_page = hxs.select('//div[@class="links"]/b/following-sibling::a[1]/@href').extract()
        items = hxs.select('//div[@class="product-grid"]/div/div[@class="image"]/a/@href').extract()

        for url in items:
            yield Request(urljoin(base_url, url), callback=self.parse_product)
        if next_page:
            yield Request(urljoin(base_url, next_page.pop()), callback=self.parse)

    def parse_price(self, price):
        try:
            price, count = re.subn(r'[^0-9 .,]*([0-9 .,]+)\W*K.*', r'\1', price.strip())
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
        elif price.isdigit():
            return float(price)
        return False

    def get_sku_from_text(self, text):
        try:
            id, count = re.subn(r'[^0-9]*([0-9]{4,6}).*', r'\1', text)
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

        name = hxs.select('//div[@id="content"]/h1/text()').extract().pop().strip()

        category = hxs.select('//div[@class="breadcrumb"]/a/text()')[-2].extract()

        sku = self.get_sku_from_text(name)

        pid = hxs.select('//input[@name="product_id"]/@value').pop().extract()
        if not sku:
            sku = pid

        price = self.parse_price(hxs.select('//div[@class="price"]/span[@class="price-new"]/text()').pop().extract())

        stock = hxs.select('//div[@class="cart"]/div[contains(text(), "Na sklad")]')

        if price:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('url', urljoin(base_url, response.url))
            loader.add_value('name', name)
            loader.add_xpath('image_url', '//div[@class="image"]/a/img[@id="image"]/@src', Compose(lambda v: urljoin(base_url, v[0])))
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

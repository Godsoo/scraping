# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader, TakeFirst
import re

from product_spiders.spiders.lego_cz.legobase import LegoMetadataBaseSpider


class BambuleSpider(LegoMetadataBaseSpider):
    name = u'bambule.cz'
    allowed_domains = ['bambule.cz', 'eshop.bambule.cz']
    start_urls = [
        u'https://eshop.bambule.cz/kategorie/lego',
    ]
    errors = []
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        next_page = hxs.select('//ul[@class="pagination"]/li[@id="pagination_next"]/a/@href').extract()
        items = hxs.select('//h2/a[@class="product_name"]/@href').extract()
        for url in items:
            yield Request(url, callback=self.parse_product)
        if next_page:
            yield Request(urljoin(base_url, next_page.pop()), callback=self.parse)

        if not items:
            retry = int(response.meta.get('retry', 0))
            if retry < 5:
                self.log('>>> Retrying No. %s => %s' % (retry, response.url))
                meta = response.meta.copy()
                meta['retry'] = retry + 1
                yield Request(response.url,
                              dont_filter=True,
                              meta=meta)
            else:
                self.log('>>> Max number of retries reached => %s' % response.url)

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

        try:
            category = hxs.select('//div[@class="breadcrumb"]//span[@itemprop="title"]/text()').extract()[-1].strip()
        except:
            category = 'LEGO'

        pid = hxs.select('//*[@itemprop="sku"]/text()').extract().pop().strip()
        if pid.endswith("LEG"):
            pid = pid[0:-3]

        price = self.parse_price(hxs.select('//*[@itemprop="price"]/text()')[-1].extract())

        stock = hxs.select('//p[@id="availability_statut"]/span[@id="availability_value"]/span[contains(@class, "availability") and contains(@class, "available")]')
        if price:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('url', urljoin(base_url, response.url))
            loader.add_xpath('name', '//*[@itemprop="name"]/text()', lambda i: i[0].strip())
            loader.add_xpath('image_url', '//img[@itemprop="image"]/@src')
            loader.add_value('price', price)
            loader.add_value('category', category)
            loader.add_value('sku', pid)
            loader.add_value('identifier', pid)
            loader.add_value('brand', 'LEGO')
            if int(price) <= 1000:
                loader.add_value('shipping_cost', 129)
            if not stock:
                loader.add_value('stock', 0)
            yield self.load_item_with_metadata(loader.load_item())
        else:
            self.errors.append("No price set for url: '%s'" % urljoin(base_url, response.url))

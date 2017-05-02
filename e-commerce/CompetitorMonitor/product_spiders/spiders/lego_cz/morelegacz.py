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


class MorelegaSpider(LegoMetadataBaseSpider):
    name = u'morelega.cz'
    allowed_domains = ['www.morelega.cz']
    start_urls = [
        u'http://www.morelega.cz/search/results.html?keywords=Lego',
    ]
    errors = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        next_page = hxs.select(u'//a[@class="pageResults"]/u[contains(text(), ">>]")]/../@href').extract()
        items = hxs.select('//table[@class="productListing"]/tr/td[1][@class="productListing-data"]/a/@href').extract()
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

        name = hxs.select('//td[@class="smallText"]/big/big/strong/text()').extract().pop().strip()

        category = hxs.select('//td[@class="headerNavigationOP"]/a[@class="headerNavigation"]/text()')[-2].extract().strip()

        sku = hxs.select('//td[@class="headerNavigationOP"]/a[@class="headerNavigation"]/text()').pop().extract().strip()
        pid = self.get_pid_from_url(response.url)

        price = self.parse_price(hxs.select('//td[@class="pageHeading"]/big[1]/strong/text()').pop().extract())

        stock = hxs.select('//td[@class="smallText"][@align="right"]/strong/big[contains(text(), "ANO")]/text()')

        if price:
            loader = ProductLoader(response=response, item=Product())
            url = response.url.split('?osCsid')[0]
            loader.add_value('url', url)
            loader.add_value('name', name)
            loader.add_xpath('image_url', '//meta[@property="og:image"]/@content', Compose(lambda v: urljoin(base_url, v[0])))
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

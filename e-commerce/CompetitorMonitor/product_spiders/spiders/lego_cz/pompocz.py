
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
import re

from product_spiders.spiders.lego_cz.legobase import LegoMetadataBaseSpider

from scrapy import log


class PompoSpider(LegoMetadataBaseSpider):
    name = u'pompo.cz'
    allowed_domains = ['www.pompo.cz']
    start_urls = [
        u'http://www.pompo.cz/lego/c-86/?page=1',
    ]
    errors = []
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//li[@class="active "]/div/ul/li/a/@href').extract()
        for category in categories:
            yield Request(category, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        next_page = hxs.select('//a[@class="next"]/@href').extract()
        items = hxs.select('//div[@class="product-list"]/ul/li/div/h2/a/@href').extract()

        for url in items:
            yield Request(url, callback=self.parse_product)
        if next_page:
            yield Request(next_page.pop(), callback=self.parse_category)

    def parse_price(self, price):
        try:
            price, count = re.subn(r'[^0-9 .,]*([0-9 .,]+) K.*', r'\1', price.strip())
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

    def get_id(self, text):
        try:
            id, count = re.subn(r'[^0-9]*([0-9]+).*', r'\1', text)
        except TypeError:
            return False
        if count:
            id = id.strip()
            try:
                int(id)
            except ValueError:
                return False
            else:
                return id
        return False
   
    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        name_xpath = '//div[@class="product-detail"]/div[@class="product-info"]/h1/text()'
        name = hxs.select(name_xpath).extract().pop().strip()

        category = hxs.select('//p[@id="breadcrumb"]/a/text()')[-1].extract()

        pid = hxs.select(u'//div[@class="base-info"]/dl/dt[contains(text(), "Katalogov\xe9 \u010d\xedslo")]/following-sibling::dd[1]/text()').extract()
        if not pid:
            pid = hxs.select('//div[@class="product-img-detail "]/a/img[@id="targetimg"]/@src').re(r'22(.*).jpg')

        if pid:
            pid = pid[0]
        else:
            log.msg('Product without identifier: ' + response.url)
            return       
            
        pid2 = self.get_id(name)
        if pid2 and len(pid2) > 3:
            if pid2 in pid:
                pid = pid2
        elif pid.startswith('22'):
            pid = pid[2:]

        price = self.parse_price(hxs.select('//div[@class="price"]/text()')[-1].extract())

        if price:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('url', urljoin(base_url, response.url))
            loader.add_value('name', name)
            loader.add_xpath('image_url', '//div[@class="product-img-detail "]/a/img[@id="targetimg"]/@src', Compose(lambda v: urljoin(base_url, v[0])))
            loader.add_value('price', price)
            loader.add_value('category', category)
            loader.add_value('sku', pid)
            loader.add_value('identifier', pid)

            yield self.load_item_with_metadata(loader.load_item())
        else:
            self.errors.append("No price set for url: '%s'" % urljoin(base_url, response.url))

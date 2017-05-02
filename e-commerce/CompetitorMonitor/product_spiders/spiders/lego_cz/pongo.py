# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
import re
from product_spiders.utils import extract_price_eu as extract_price
from urlparse import urljoin as urljoin_rfc
from decimal import Decimal
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from product_spiders.spiders.lego_cz.legobase import LegoMetadataBaseSpider


class PongoSpider(LegoMetadataBaseSpider):
    name = u'pongo.cz'
    allowed_domains = ['www.pongo.cz']
    start_urls = [
        u'http://www.pongo.cz/lego',
    ]
    errors = []
    items = {}
    later_ids = ['5702015153591', '5702015153584']

    def __init__(self, *args, **kwargs):
        super(PongoSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        if self.items:
            request = Request(self.start_urls[0], dont_filter=True, callback=self.closing_parse)
            self._crawler.engine.crawl(request, self)

    def closing_parse(self, response):
        self.log("Processing items after finish")
        for item in self.items.values():
            yield item

        self.items = None

    def later(self, product):
        identifier = product.get('identifier')
        if identifier in self.items:
            if product.get('price', 0) and product.get('price', 0) < self.items[identifier].get('price', 0):
                self.items[identifier] = product
        else:
            self.items[identifier] = product

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse pagination
        urls = hxs.select('//div[@class="pages"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)
        # products list
        urls = hxs.select('//div[@class="productitem"]//h2/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//*[@id="main"]//h1/text()').extract()[0]
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_xpath('image_url', '//*[@id="images"]/ul/li/a/img/@src',
                         Compose(lambda v: urljoin(base_url, v[0])))
        price = hxs.select('//*[@id="buy"]//p[@class="price"]/big/text()').extract()[0]
        price = extract_price(price.replace(' ', ''))
        loader.add_value('price', price)
        category = hxs.select('//div[@class="category"]//li/a[@class="sel"]/text()').extract()
        if category:
            loader.add_value('category', category[-1])
        sku = ''
        for match in re.finditer(r"([\d,\.]+)", name):
            if len(match.group()) > len(sku):
                sku = match.group()
        loader.add_value('sku', sku)
        identifier = hxs.select('//*[@id="parametters"]/table//th[contains(text(), "EAN")]/following-sibling::td/text()').extract()[0]
        loader.add_value('identifier', identifier)
        availability = hxs.select('//*[@id="buy"]//p[@class="availability"]/span/text()').extract()[0].strip()
        if availability != 'Skladem':
            loader.add_value('stock', 0)
        loader.add_value('brand', 'LEGO')
        if int(price) <= 1000:
            loader.add_value('shipping_cost', 95)
        product = self.load_item_with_metadata(loader.load_item())
        if product.get('identifier') in self.later_ids:
            self.later(product)
            return
        yield product

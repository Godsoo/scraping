# -*- coding: utf-8 -*-
import re
from urlparse import urljoin

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price_eu as extract_price

from product_spiders.spiders.lego_cz.legobase import LegoMetadataBaseSpider


class MallCzSpider(LegoMetadataBaseSpider):
    name = u'mall.cz'
    allowed_domains = ['www.mall.cz']
    start_urls = [
        u'http://www.mall.cz/lego',
    ]
    download_delay = 1.0
    errors = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # subcategories
        urls = hxs.select('//*[@class="lst-guide-item-title"]/a/@href').extract()
        urls += hxs.select('//ul[contains(@class, "nav-secondary")]//li[@class="nav-secondary--primary"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin(base_url, url), callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse pagination
        urls = hxs.select('//a[contains(@class, "nav-pagin-item")]/@href').extract()
        for url in urls:
            yield Request(urljoin(base_url, url), callback=self.parse_categories)
        # products
        urls = hxs.select('//h3[@class="lst-product-item-title"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//*[@itemprop="name"]/text()').extract()[0].strip()
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_xpath('image_url', '//img[@ng-src="{{mainImage()}}"]/@src')
        price = hxs.select('//*[@itemprop="price"]/text()').extract()[0].strip()
        price = extract_price(price.replace(' ', '').replace(u'\xa0', ''))
        loader.add_value('price', price)
        category = hxs.select('//a[@class="nav-crumb-item"]/text()').extract()
        if category:
            loader.add_value('category', category[-1])
        sku = ''
        for match in re.finditer(r"([\d,\.]+)", name):
            if len(match.group()) > len(sku):
                sku = match.group()
        loader.add_value('sku', sku)
        identifier = hxs.select('//article/@data-variantid').extract()[0]
        loader.add_value('identifier', identifier.strip())
        availability = hxs.select('//*[@class="label label--stock"]//text()').extract()
        if not availability:
            stock = 0
        elif availability[0].strip().lower() != u'Skladem MALL'.lower():
            stock = 0
        else:
            stock = None
        loader.add_value('stock', stock)
        loader.add_value('brand', 'LEGO')
        yield self.load_item_with_metadata(loader.load_item())

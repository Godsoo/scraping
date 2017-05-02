# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price_eu
from copy import deepcopy
import re


class HakmaseSpider(BaseSpider):
    name = u'hakma.se'
    allowed_domains = ['www.hakma.se']
    start_urls = [
        u'http://www.hakma.se/',
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//div[@class="AspNet-TreeView"]/ul/li//a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_category)


    def parse_category(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//tr[@class="ItemTemplate" or @class="AlternatingItemTemplate"]')
        for product in products:
            image_url = product.select('td[1]/img/@src').extract()
            identifier = product.select('td[2]/a/text()').extract()[0]
            name = product.select('td[3]/a/text()').extract()[0].strip()
            url = product.select('td[2]/a/@href').extract()[0]
            url = urljoin_rfc(base_url, url)
            categories = hxs.select('//div[@class="BreadCrumb"]/div/a/text()').extract()
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('url', url)
            loader.add_value('name', name)
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0].replace('_thumb.jpg', '.jpg')))
            for category in categories:
                loader.add_value('category', category)
            out_of_stock = product.select('.//input[contains(@id, "txtQuantity") and @disabled]')
            if out_of_stock:
                loader.add_value('stock', 0)
            else:
                loader.add_value('stock', 1)
            loader.add_value('sku', identifier)
            loader.add_value('identifier', identifier)

            yield Request(url, meta={'loader': loader}, callback=self.parse_price)

        next_page = hxs.select('//a[contains(@id, "_lnkNext")]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), callback=self.parse_category)


    def parse_price(self, response):

        hxs = HtmlXPathSelector(response)
        loader = response.meta['loader']

        price = hxs.select("//span[@id='ctl00_ctpMain_ctl00_ctl00_lblPrice']/text()").extract()[0].strip()
        price = extract_price_eu(price)
        loader.add_value('price', price)

        yield loader.load_item()

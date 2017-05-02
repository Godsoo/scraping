# -*- coding: utf-8 -*-
import os
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class WestWingNowSpider(BaseSpider):
    name = 'made_de-westwingnow.de'
    allowed_domains = ['westwingnow.de']
    start_urls = ['https://www.westwingnow.de']

    def _start_requests(self):
        yield Request('https://www.westwingnow.de/tischleuchte-felicitas-2er-set-13912.html', callback=self.parse_product)

    def parse(self, response):
        # categories = response.xpath('//nav[@class="h__nav1 js-mobile-nav-block"]/ul/li/a/@href').extract()
        categories = response.xpath('//ul[@class="blockNavigation jsNavigation"]//a/@href').extract()
        for url in categories:
            url = response.urljoin(url)
            url = add_or_replace_parameter(url, 'sort', 'price_asc')
            url = add_or_replace_parameter(url, 'dir', 'asc')
            yield Request(url)

        next_page = response.xpath('//a[contains(@class,"cl__pagList__link") and span[@class="icon-right"]]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]))

        products = response.xpath('//*[contains(@class,"cl__list__item")]/a[descendant::div[@class="cl__list__nameAndBrand"]]/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product)

    def parse_product(self, response):
        categories = response.xpath('//li[@class="blockBreadcrumb__item"]/a/text()').extract()[-3:]

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('identifier', '//input[@name="simpleSku"]/@value')
        loader.add_xpath('sku', '//input[@id="configSku"]/@value')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[contains(@class, "__heading")]/text()')
        loader.add_xpath('name', '//input[@name="simpleSku"]/../span/text()')
        loader.add_xpath('image_url', '//div[@class="layoutImage"]//img/@src')
        loader.add_xpath('price', '//input[@id="price"]/@value')
        loader.add_xpath('brand', '//input[@id="brand"]/@value')
        loader.add_value('category', categories)
        loader.add_xpath('stock', '//@data-instock')
        item = loader.load_item()
        
        options = response.xpath('//select[@id="js-simple-selector"]/option')
        if not options:
            if loader.get_output_value('identifier'):
                yield item
            return
        for option in options:
            loader = ProductLoader(item=Product(item), selector=option)
            loader.replace_xpath('identifier', './@value')
            loader.add_xpath('name', './text()')
            identifier = loader.get_output_value('identifier')
            price = response.xpath('//div[@data-simple-sku="%s"]//span[contains(@class, "actualPrice")]/text()' %identifier).extract()
            loader.replace_value('price', price)
            image_url = response.xpath('//div[@data-simple-sku="%s"]/a[contains(@class, "link_selected")]/@data-product-image' %identifier).extract()
            loader.replace_value('image_url', image_url)
            loader.replace_xpath('stock', './@data-instock')
            yield loader.load_item()

# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc

from scrapy import log


class BestSadRuSpider(BaseSpider):
    name = u'husqvarna-russia-best-sad.ru'
    allowed_domains = ['best-sad.ru']
    start_urls = ['http://www.best-sad.ru/?get_tree=1&home=1']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)


        for cat in hxs.select('//a/@href').extract():
            yield Request(urljoin_rfc(base_url, cat), callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        sub_categories = hxs.select('//div[@class="catalog-prod-bl"]/ul/li/a/@href').extract()
        for sub_cat in sub_categories:
            yield Request(urljoin_rfc(base_url, sub_cat), callback=self.parse_categories)

        # if not sub_categories:
        products = hxs.select('//div[@class="name-brief"]/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        next_page = hxs.select('//ul[@class="pagination"]/li/a[contains(text(), ">")]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), callback=self.parse_categories)

    @staticmethod
    def parse_product(response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//ul[@class="slides"]/li/a/img/@src').extract()
        product_identifier = hxs.select('//input[@name="productID"]/@value').extract()
        if not product_identifier: 
            log.msg('PRODUCT WITHOUT IDENTIFIER: ' + response.url)
            return
        product_identifier = product_identifier[0].strip()
        product_name = hxs.select('//div[@class="sliders-card-prod"]/h1/text()').extract()[0].strip()
        #brand = hxs.select('//div[@class="nav"]/div//span[@itemprop="title"]/text()').extract()
        #brand = brand[-1].strip() if brand else ''

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('identifier', product_identifier)
        loader.add_value('name', product_name)
        sku = hxs.select('//ul[@class="c-prod-info-top"]/li/text()').re('# (.*)')
        sku = sku[0] if sku else ''
        loader.add_value('sku', sku)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        price = ''.join(hxs.select('//p[@class="price-buy"]/text()').extract()).strip()
        if price:
            loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_value('brand', '')
        categories = hxs.select('//div[@class="bread-crumbs"]/ul/li/a/text()').extract()[1:]
        for category in categories:
            loader.add_value('category', category)
        product = loader.load_item()
        yield product

# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price_eu as extract_price


class KlimastoreSpider(BaseSpider):
    name = u'klimastore.net'
    allowed_domains = ['www.klimastore.net']
    start_urls = ('http://www.klimastore.net/it/', )
    brands = []

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        self.brands = hxs.select('//*[@id="manufacturer_list"]/option/text()').extract()[1:]
        for url in hxs.select('//ul[@class="tree dhtml"]/li/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url + '?n=50&p=1'), callback=self.parse_product_list)

    def parse_product_list(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//*[@id="product_list"]//h3/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        for url in hxs.select('//*[@id="pagination"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//*[@id="primary_block"]/h1/text()').extract()[0]
        loader.add_value('name', name)
        identifier = hxs.select('//input[@name="id_product"]/@value').extract()[0]
        # if not identifier:
        #     return
        loader.add_value('identifier', identifier)
        sku = hxs.select('//span[@class="editable"]/text()').extract()
        if sku:
            loader.add_value('sku', sku[0].strip())
        loader.add_value('url', response.url)
        image_url = hxs.select('//*[@id="bigpic"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        price = hxs.select('//*[@id="our_price_display"]/text()').extract()
        # if not price:
        #     return
        price = extract_price(price[0].replace(' ', ''))
        loader.add_value('price', price)
        brand = None
        for b in self.brands:
            if b in name:
                brand = b
                break
        if brand:
            loader.add_value('brand', brand)
        category = hxs.select('//div[@class="breadcrumb"]/a[2]/text()').extract()
        if category:
            loader.add_value('category', category[0])
        yield loader.load_item()
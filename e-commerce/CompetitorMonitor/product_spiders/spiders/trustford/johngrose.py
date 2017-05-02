# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
import re
import json


class JohngroseSpider(BaseSpider):
    name = u'trustford-johngrose.co.uk'
    allowed_domains = ['www.johngrose.co.uk']
    start_urls = ('http://www.johngrose.co.uk/newcars/ford', )

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//a[@class="newcar-select"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        #models
        if not 'no_options' in response.meta:
            for url in hxs.select('//div[contains(@class, "new-car-variants")]/a/@href').extract():
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'no_options': True})
        loader = ProductLoader(item=Product(), selector=hxs)
        car = hxs.select('//h1/text()').extract()[0].strip()
        try:
            model = hxs.select('//div[contains(@class, "new-car-variants")]/a[@class="active"]/text()').extract()[0].strip()
        except IndexError:
            return
        engine_cc = hxs.select('//h2[text()="Engine"]/following-sibling::li[1]/ul/li/span[text()="Badge Engine CC:"]/following-sibling::span[@class="value"]/text()').extract()[0].strip()
        power = hxs.select('//h2[text()="Performance"]/following-sibling::li[1]/ul/li/span[text()="Engine Power:"]/following-sibling::span[@class="value"]/text()').extract()[0].strip()
        name = ', '.join((car, model, engine_cc, power))
        loader.add_value('name', name)
        identifier = response.url.strip('/').split('/')[-1]
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        price = hxs.select('//td[contains(.,"On the road cash price")]/following-sibling::td[1]//text()').extract()
        if not price:
            price = hxs.select('//td[contains(.,"Monthly payments")]/following-sibling::td[1]//strong/text()').extract()
        loader.add_value('price', price)
        
        yield loader.load_item()
        
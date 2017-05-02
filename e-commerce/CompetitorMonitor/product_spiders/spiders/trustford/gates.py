# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
import re


class GatesSpider(BaseSpider):
    name = u'trustford-gates.co.uk'
    allowed_domains = ['www.gates.co.uk']
    start_urls = ('http://www.gates.co.uk/new-car-offers/', )

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//div[@class="list-item "]//h3/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    @staticmethod
    def parse_product(response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        price = hxs.select('//*[@class="data"]//td[contains(text(), "Cash Price")]/../td[2]/text()').extract()
        if price:
            price = extract_price(price[0])
            name = hxs.select('//h2[1]/text()').extract()[0]
            name = name.replace('New ', '').replace(' Offer Enquiry', '').split(' from ')[0]
            loader.add_value('name', name)
            loader.add_value('price', price)
            identifier = re.findall("new-car-offers/([a-zA-Z0-9\-]+)", response.url)[0]
            loader.add_value('identifier', identifier)
            loader.add_value('url', response.url)
            yield loader.load_item()

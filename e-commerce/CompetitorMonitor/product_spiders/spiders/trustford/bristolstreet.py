# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price


class BristolstreetSpider(BaseSpider):
    name = u'trustford-bristolstreet.co.uk'
    allowed_domains = ['www.bristolstreet.co.uk']
    start_urls = ('http://www.bristolstreet.co.uk/new-car-deals/ford/', )

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//*[@id="modelLevelHub"]/li/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//*[@id="UCsearchRdropdown"]//div[@class="pageLinks"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products)
        cars = hxs.select('//div[@itemtype="http://schema.org/Product"]')
        for car in cars:
            loader = ProductLoader(item=Product(), selector=hxs)
            name = car.select('.//h3[@itemprop="name"]/a/text()').extract()[0].strip()
            url = car.select('.//h3[@itemprop="name"]/a/@href').extract()[0]
            price = car.select('.//p[@itemprop="lowPrice"]/text()').extract()[0]
            price = extract_price(price)
            image_url = car.select('//div[@class="vehImageSection"]/a/img/@src').extract()
            image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
            loader.add_value('image_url', image_url)
            loader.add_value('price', price)
            loader.add_value('name', name)
            loader.add_value('url', urljoin_rfc(base_url, url))
            identifier = url.split('/')[-2]
            loader.add_value('identifier', identifier)
            yield loader.load_item()
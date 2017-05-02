# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from urlparse import urljoin

from product_spiders.utils import extract_price

class EssexautogroupSpider(BaseSpider):
    name = u'trustford-essexautogroup.com'
    allowed_domains = ['www.essexautogroup.com']
    start_urls = ('http://www.essexautogroup.com/ford/new-offers/', )

    def _start_requests(self):
        yield Request('http://www.essexautogroup.com/ford/new-offers/ford-btourneob-connect/', callback=self.parse_product)


    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//div[@class="list-item "]//a[@title="View Offer"]/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_product)

    @staticmethod
    def parse_product(response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        models = response.xpath('//div[contains(@class, "row-fluid") and .//table[@class="data"] and div[contains(@class, "media span")]]')
        for model in models:
            loader = ProductLoader(item=Product(), selector=model)
            name = model.xpath('.//p/strong//text()').extract()[-1].strip()
            if not name:
                name = model.xpath('.//p/strong[contains(text(), "Ford")]//text()').extract()[-1].strip()
            loader.add_value('name', name)
            prices = model.xpath('.//tr[td[contains(text(), "Cash")]]/td[not(contains(text(), "Cash"))]/text()').re('\d+,\d+')
            prices = map(extract_price, prices)
            price = min(prices)
            loader.add_value('price', price)
            image_url = model.xpath('.//picture/source/@data-placeholder').extract()
            image_url = 'http:' + image_url[0] if image_url else ''
            loader.add_value('image_url', image_url)
            loader.add_value('identifier', '_'.join(name.split()))
            loader.add_value('url', response.url)
            yield loader.load_item()

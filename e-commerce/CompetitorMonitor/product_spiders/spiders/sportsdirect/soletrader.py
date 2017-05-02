# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc


class SoletraderCoUkSpider(BaseSpider):
    name = u'soletrader.co.uk'
    allowed_domains = ['www.soletrader.co.uk']
    start_urls = [
        'http://www.soletrader.co.uk/nike'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = hxs.select('//div[@class="st_occasion"]//li/a/@href').extract()
        categories = hxs.select('//div[@class="st_occasion"]//li/a/@title').extract()
        for url, category in zip(urls, categories):
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list1, meta={'category': category})

    def parse_products_list1(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        url = hxs.select('//li[@class="view-all"]/a/@href').extract()[0]
        yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list2, meta=response.meta)

    def parse_products_list2(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@class="thumbnail"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//div[@class="info"]/h1/text()').extract()[0].strip()
        url = response.url
        loader.add_value('url', urljoin_rfc(base_url, url))
        loader.add_value('name', name)
        image_url = hxs.select('//*[@id="mainimage"]/img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        loader.add_value('category', response.meta.get('category'))
        price = hxs.select('//div[@class="info"]//p[@class="price clearfix"]/span/text()').extract()
        price = ''.join(price).strip().replace(u'\xa3', '')
        price = extract_price(price)
        loader.add_value('price', price)
        identifier = hxs.select('//div[@class="info"]/h1/span/text()').extract()[0].strip()[1:-1]
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('brand', 'Nike')
        if price < 35:
            loader.add_value('shipping_cost', 2.99)
        else:
            loader.add_value('shipping_cost', 0)
        yield loader.load_item()
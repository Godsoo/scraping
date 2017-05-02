# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price_eu as extract_price
from urlparse import urljoin as urljoin_rfc


class RakutenEsSpider(BaseSpider):
    name = u'rakuten.es'
    allowed_domains = ['rakuten.es']
    start_urls = [
        'http://www.rakuten.es/tienda/purnima-digital/productos/?h=3&l-id=es_search_show_60'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # products
        for url in hxs.select('//div[@class="b-container"]//div[@class="b-text"]/div/b/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        # pagination
        for url in hxs.select('//div[@class="b-container b-pagination b-center"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)

    @staticmethod
    def parse_product(response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        #image_url = hxs.select('//div[contains(@class, "b-main-image")]/a/@href').extract()
        image_url = hxs.select('//img[@itemprop="image"]/@data-frz-src').extract()
        product_identifier = hxs.select('//input[@name="sku"]/@value').extract()[0]
        product_name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0].strip()
        price = hxs.select('//div[@id="auto_show_prime_price"]/strong/span[contains(@class, "actualPrice")]/text()').extract()[0]
        price = extract_price(price)
        category = hxs.select('//ul[@class="b-breadcrumb"]//a/text()').extract()[1:]
        brand = hxs.select('//span[@itemprop="brand"]/text()').extract()
        brand = brand[0] if brand else ''

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('name', product_name)
        if image_url:
            product_loader.add_value('image_url', image_url[0])
        product_loader.add_value('sku', product_identifier)
        product_loader.add_value('price', price)
        product_loader.add_value('url', response.url)
        product_loader.add_value('category', category)
        product_loader.add_value('brand', brand)
        product = product_loader.load_item()
        yield product

# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc


class ExpeditelectronicsComSpider(BaseSpider):
    name = u'expeditelectronics.com'
    allowed_domains = ['www.expeditelectronics.com']
    start_urls = [
        'http://www.expeditelectronics.com/shopping.html?mode=grid'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # products
        for url in hxs.select('//*[@id="narrow-by-list"]/dd[1]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # products
        for url in hxs.select('//div[@class="category-products"]//h2[@class="product-name"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        # pagination
        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products)

    @staticmethod
    def parse_product(response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//meta[@itemprop="image"]/@content').extract()
        product_identifier = hxs.select('//input[@name="product"]/@value').extract()[0]
        product_name = hxs.select('//div[@class="product-name"]//h1/div/text()').extract()[0].strip()
        price = hxs.select('//meta[@itemprop="price"]/@content').extract()
        price = extract_price(price[0])
        category = hxs.select('//meta[@itemprop="category"]/@content').extract()[0].split('>')
        if not ''.join(category):
            category = hxs.select('//div[@class="breadcrumbs"]/ul/li/a/text()').extract()[2:]

        brand = hxs.select('//meta[@itemprop="brand"]/@content').extract()
        sku = hxs.select('//meta[@itemprop="sku"]/@content').extract()
        stock = hxs.select('//p[@class="availability out-of-stock"]').extract()

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('name', product_name)
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        product_loader.add_value('sku', sku)
        product_loader.add_value('price', price)
        product_loader.add_value('url', response.url)
        product_loader.add_value('category', category)
        product_loader.add_value('brand', brand)
        if stock:
            product_loader.add_value('stock', 0)
        product = product_loader.load_item()
        yield product

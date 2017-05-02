# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc


class PanamozComSpider(BaseSpider):
    name = u'panamoz.com'
    allowed_domains = ['panamoz.com']
    start_urls = [
        'http://panamoz.com'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//a[@class="itemMenuName level1"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url + '?limit=30'), callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # products
        brand = hxs.select('//div[@class="breadcrumbs"]//strong/text()').extract()
        brand = brand[0] if brand else ''
        for url in hxs.select('//div[@class="category-products"]//h2[@class="product-name"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'brand': brand})
        # pagination
        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

    @staticmethod
    def parse_product(response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//p[@class="product-image"]/a/@href').extract()
        product_identifier = hxs.select('//input[@name="product"]/@value').extract()[0]
        product_name = hxs.select('//div[@class="product-name"]/h1/text()').extract()[0].strip()
        price = hxs.select('//div[@class="short-description"]/div/p/span/strong/span/text()').extract()
        if not price:
            price = hxs.select('//div[@class="price-box"]//span[@class="price"]/text()').extract()
        price = extract_price(price[0])
        category = hxs.select('//div[@class="breadcrumbs"]//a/text()').extract()[1]
        brand = response.meta.get('brand', '')
        stock = hxs.select('//p[@class="availability out-of-stock"]').extract()

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('name', product_name)
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        product_loader.add_value('sku', product_identifier)
        product_loader.add_value('price', price)
        product_loader.add_value('url', response.url)
        product_loader.add_value('category', category)
        product_loader.add_value('brand', brand)
        if stock:
            product_loader.add_value('stock', 0)
        product = product_loader.load_item()
        yield product
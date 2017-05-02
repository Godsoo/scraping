import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url
from product_spiders.items import (Product,
        ProductLoaderWithNameStrip as ProductLoader)
from scrapy import log
from urlparse import urlparse

class AquariumSuperStore(BaseSpider):
    name = 'aquariumsuperstore.co.uk'
    allowed_domains = [
            'www.aquariumsuperstore.co.uk',
            'aquariumsuperstore.co.uk',
            ]
    start_urls = [
            'http://www.aquariumsuperstore.co.uk/',
            ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select(
                "//div/ul/li/a[contains(@href, 'http')]/@href").extract()
        for category in categories:
            yield Request(
                    url=canonicalize_url(category),
                    callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        sub_categories = hxs.select(
                '//dl[@id="narrow-by-list2"]/dd/ol/li/a/@href').extract()
        if sub_categories:
            for sub_cat in sub_categories:
                yield Request(
                        url=canonicalize_url(urljoin_rfc(base_url, sub_cat)),
                        callback=self.parse_products)

        products = hxs.select(
                '//li[@class="item" or @class="item first"'
                ' or @class="item last"]')
        if products:
            for product in products:
                url = product.select('h2/a/@href').extract()
                if url:
                    yield Request(
                            url=url[0],
                            callback=self.parse_product)

            next = hxs.select('//a[@class="next i-next"]/@href').extract()
            if next:
                yield Request(
                        url=next[0],
                        callback=self.parse_products)

        sub_categories = hxs.select(
                '//div[@class="feat-cat-content"]/a/@href').extract()
        if sub_categories:
            for sub_cat in sub_categories:
                yield Request(
                        url=canonicalize_url(urljoin_rfc(base_url, sub_cat)),
                        callback=self.parse_products)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//div[@class="product-view"]/div/div/div[@class="category-title-img"]/text()')
        loader.add_value('url', response.url)
        loader.add_xpath('sku', '//div[@class="product-name"]/span[1]/text()')
        loader.add_xpath('identifier', '//div[@class="product-name"]/span[1]/text()')
        loader.add_xpath('image_url', '//p[@class="product-image"]/img/@src')
        loader.add_xpath('brand', '//div[@class="manufacturer_cont"]/span/a/@title')

        price = hxs.select('//div[@class="product-shop"]/div[@class="price-box"]/span[@class="regular-price"]/span[@class="price"]/text()').extract()
        if price:
            price = price[0]
        else:
            price = hxs.select('//p[@class="special-price"]/span[@class="price"]/text()').extract()
            if price:
                price = price[0]
            else:
                price = hxs.select('//span[@class="regular-price"]/span[@class="price"]/text()').extract()
                if price:
                    price = price[0]
        loader.add_value('price', price)
        yield loader.load_item()
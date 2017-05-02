# -*- coding: utf-8 -*-
import os

from scrapy.spider import BaseSpider
from scrapy.http import HtmlResponse, Request

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

here = os.path.abspath(os.path.dirname(__file__))


class PriceRunner(BaseSpider):
    name = "specsavers_sw-pricerunner.se"
    allowed_domains = ["pricerunner.se"]
    start_urls = ['http://www.pricerunner.se/cl/334/Kontaktlinser']

    def parse(self, response):
        products = response.xpath('//div[contains(@id, "prod-")]')
        for p in products:
            loader = ProductLoader(item=Product(), selector=p)
            product_data = p.xpath('@product-data').extract()[0].split('|')
            url = p.xpath('.//h3/a/@href').extract()[0]
            url = response.urljoin(url)
            name = p.xpath('.//h3/a/text()').extract()[0].strip()
            price = ''.join(p.xpath('.//p[@class="price-rang"]/a/text()').extract()[0].split())
            image_url = p.xpath('.//div[contains(@class, "productimg")]/a/img/@src').extract()[0].strip()
            identifier = product_data[1]
            brand = product_data[3]
            categories = response.xpath('//div[@id="breadcrumbs"]//a/text()').extract()[2:]
            dealer = p.xpath('.//div[@class="retailerlogo"]/a/@retailer-data').re('(.*)\(')[0]
            out_of_stock = p.xpath('.//div[@class="stock-info"]/a/p[contains(@class, "out-of-stock")]')

            loader.add_value('url', url)
            loader.add_value('price', price)
            loader.add_value('brand', brand)
            loader.add_value('category', categories)
            loader.add_value('name', name)
            loader.add_value('image_url', image_url)
            loader.add_value('identifier', identifier)
            loader.add_value('sku', identifier)
            loader.add_value('dealer', dealer)
            if out_of_stock:
                loader.add_value('stock', 0)
            yield loader.load_item()

        pages = response.xpath('//div[@class="paginator"]//a/@href').extract()
        for page in pages:
            yield Request(response.urljoin(page))

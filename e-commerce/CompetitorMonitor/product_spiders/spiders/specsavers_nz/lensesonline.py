# -*- coding: utf-8 -*-
"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4572
"""
from scrapy import Spider, Request

from product_spiders.items import ProductLoaderWithNameStrip, Product


class LensesOnline(Spider):
    name = 'specsavers_nz-lenses_online'
    allowed_domains = ('lensesonline.co.nz', )

    start_urls = ['http://www.lensesonline.co.nz/']

    def parse(self, response):
        for cat_url in response.xpath("//div[@id='SideCategoryList']//ul/li/a/@href").extract():
            yield Request(cat_url, callback=self.parse_category)

    def parse_category(self, response):
        for page_url in response.xpath("//ul[@class='PagingList']/li/a/@href").extract():
            yield Request(page_url, callback=self.parse_category)

        for prod_url in response.xpath("//ul[contains(@class, 'ProductList')]/li/div[@class='ProductDetails']/a/@href").extract():
            yield Request(prod_url, callback=self.parse_product)

    def parse_product(self, response):
        name = response.xpath("//h1[@itemprop='name']/text()").extract()[0]
        price = response.css('span.ProductPrice::text').extract()
        cats = response.xpath("//div[@id='ProductBreadcrumb']/ul/li//text()").extract()[1:-1]
        brand = ''.join(response.xpath("//*[@itemprop='brand']//text()").extract()).strip()
        if not brand:
            raise ValueError('brand')
        shipping_cost = 5
        sku = response.xpath("//*[@itemprop='sku']/text()").extract()[0].strip()
        identifier = response.xpath("//input[@name='product_id']/@value").extract()[0]
        image_url = response.xpath("//*[@itemprop='image']/@src").extract()[0]

        loader = ProductLoaderWithNameStrip(Product(), response=response)

        loader.add_value('name', name)
        loader.add_value('price', price.pop())
        loader.add_value('url', response.url)
        loader.add_value('brand', brand)
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier)
        loader.add_value('image_url', image_url)
        loader.add_value('category', cats)
        loader.add_value('shipping_cost', shipping_cost)

        yield loader.load_item()
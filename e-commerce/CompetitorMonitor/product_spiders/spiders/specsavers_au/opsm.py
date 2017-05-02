# -*- coding: utf-8 -*-
"""
Extract all products without options

Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/4563-specsavers-au--amp--nz---new-site---opsm/details
"""
import os

from scrapy.spider import BaseSpider
from scrapy.http import Request

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

from specsaversitems import SpecSaversMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class OPSMSpider(BaseSpider):
    name = 'specsavers_au-opsm.com.au'
    allowed_domains = ('opsm.com.au',)
    start_urls = ('https://www.opsm.com.au/',)

    def parse(self, response):
        categories = response.xpath('//nav[@class="global-nav"]//a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url))

        products = response.xpath('//div[@class="products"]//div[@class="data"]/a/@href').extract()
        for url in products:
            banner = response.xpath('//div[@class="hero-box brand"]//img[contains(@src, "Buy3")]')
            promotional_data = 'Buy 3 boxes, get 1 free' if banner else ''
            yield Request(response.urljoin(url), callback=self.parse_product, meta={'promotional_data': promotional_data})

        view_all = response.xpath('//a[@class="all viewAllTop  "]/@href').extract()
        if view_all:
            yield Request(response.urljoin(view_all[0]))

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        name = ' '.join(response.xpath('//div[@itemprop="name"]/*//text()').extract())
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        image_url = response.xpath('//img[@class="left-image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url[0]))
        price = response.xpath('//div[@itemprop="offers"]/p[@class="box-price"]/b/text()').extract()
        if not price:
            price = response.xpath('//div[@itemprop="offers"]/span[@itemprop="price"]/text()').extract()
        loader.add_value('price', price)
        brand = response.xpath('//img[@class="brand"]/@alt').extract()
        if not brand:
            brand = response.xpath('//div[@itemprop="name"]/h1/text()').extract()
        if brand and not brand[0].isdigit():
            loader.add_value('brand', brand)
        sku = response.xpath('//input[@type="hidden" and @name="productIdAnalytics"]/@value').extract()
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)
        item = loader.load_item()

        metadata = SpecSaversMeta()
        metadata['promotion'] = response.meta['promotional_data']
        item['metadata'] = metadata
        yield item

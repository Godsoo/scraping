# -*- coding: utf-8 -*-
"""
Extract all products without options

Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/4565-specsavers-au---new-site---bupa-optical/details
"""
import os
import re

from scrapy.spider import BaseSpider
from scrapy.http import Request

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

from specsaversitems import SpecSaversMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class BupaOpticalSpider(BaseSpider):
    name = 'specsavers_au-bupaoptical.com.au'
    allowed_domains = ('bupaoptical.com.au',)
    start_urls = ('https://www.bupaoptical.com.au/',)

    def parse(self, response):
        categories = response.xpath('//a[@class="menu-heading"]/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url))

        products = response.xpath('//div[@class="products"]//a[contains(@class,"product")]/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product)

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        name = response.xpath('//h1[@itemprop="name"]/text()').extract()
        if not name:
            name = response.xpath('//script[contains(text(), "ec:addProduct")]').re('name\': \'(.*)\',')
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url[0]))
        price = response.xpath('//span[@itemprop="price"]/text()').extract()
        if not price:
            price = response.xpath('//script[contains(text(), "ec:addProduct")]').re('price\': (.*)')
        loader.add_value('price', price)
        categories = response.xpath('//div[@class="breadcrumbs"]/a/text()')[1:].extract()
        for category in categories:
            loader.add_value('category', category)
        brand = response.xpath('//a[@itemprop="brand"]/text()').extract()
        if not brand:
            brand = response.xpath('//script[contains(text(), "ec:addProduct")]').re('brand\': \'(.*)\',')
        loader.add_value('brand', brand)
        sku = response.xpath('//h2[@class="blueH2" and contains(text(),"SKU")]/text()').re('SKU (.*)')
        loader.add_value('sku', sku)
        identifier = re.search('.*/(.*)$', response.url).group(1)
        loader.add_value('identifier', identifier)
        item = loader.load_item()

        metadata = SpecSaversMeta()
        promotional_data = response.xpath('//div[@class="price" and label[contains(text(), "Bupa Member")]]//text()').extract()
        promotional_data = ' '.join(map(lambda x: x.strip(), promotional_data))
        metadata['promotion'] = promotional_data
        item['metadata'] = metadata
        yield item

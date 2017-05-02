# -*- coding: utf-8 -*-
"""
Customer: GuitarGuitar
Website: http://www.juno.co.uk
Extract all products from DJ Equipment category
"""

import re
from urlparse import urljoin as urljoin_rfc

from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider

from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price


class JunoCoUkSpider(BaseSpider):

    name = u'guitarguitar-juno.co.uk'
    allowed_domains = ['www.juno.co.uk']
    start_urls = ['http://www.juno.co.uk/dj-equipment/?&currency=GBP',
                  'http://www.juno.co.uk/studio-equipment/?&currency=GBP']


    def parse(self, response):

        categories = response.xpath('//div[contains(@class, "dj_equipment_navigation")]//a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category) + '?&currency=GBP')

        products = response.xpath('//div[@class="product-list"]/div[@class="dv-item"]')
        for product in products:
            try:
                name = product.xpath('.//a[@class="text_medium text_fg"]/text()').extract()[0]
            except:
                continue
            url = product.xpath('.//a[@class="text_medium text_fg"]/@href').extract()[0]
            url = response.urljoin(url)
            identifier = url.split('/')[-2]
            image_url = "http://images.junostatic.com/full/IS" + str(identifier) + "-01-BIG.jpg"
            image_url = response.urljoin(image_url)
            price = product.xpath('.//span[@class="price_lrg"]/text()').extract()
            price = extract_price(price[0])
            brand = ''.join(product.xpath('.//div[@class="vi-text mb_sml"]/a/text()').extract()	)
            sku = ''.join(product.select('.//div/text()').re('Cat: (.*) Rel:'))
            stock = product.select('.//span[@id="curstock"]')
            categories = response.xpath('//div[@class="breadcrumb_text"]/a/text()').extract()
            categories += response.xpath('//div[@class="breadcrumb_text"]/h1/text()').extract()
            categories = categories[1:]

            loader = ProductLoader(item=Product(), selector=products)
            loader.add_value('name', name)
            loader.add_value('identifier', identifier)
            loader.add_value('url', url)
            loader.add_value('brand', brand)
            loader.add_value('image_url', image_url)
            loader.add_value('price', price)
            loader.add_value('sku', sku)
            if not stock:
                loader.add_value('stock', 0)
            loader.add_value('category', categories)
            yield loader.load_item()

        next = response.xpath('//a[contains(@title, "Next")]/@href').extract()
        if next:
            yield Request(response.urljoin(next[0]))


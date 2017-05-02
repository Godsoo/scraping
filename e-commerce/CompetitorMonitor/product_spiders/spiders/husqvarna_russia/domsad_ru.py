# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy import log
from product_spiders.items import Product, ProductLoader
import re


class DomsadRuSpider(BaseSpider):
    name = u'domsad_ru'
    allowed_domains = ['tehnosad.ru']
    start_urls = [
        'http://www.tehnosad.ru/'
    ]

    def parse(self, response):
        categories = response.xpath('//div[@class="item-label"]/a/@href').extract()
        categories += response.xpath('//div[@class="categ-node"]//a[@class="node-link"]/@href').extract()
        categories += response.xpath('//div[@class="types-descr"]/a/@href').extract()
        categories += response.xpath('//a[@class="subcatalog-link "]/@href').extract()
        categories += response.xpath('//ul[@class="vyp-menu"]//a[contains(@href,"subcategory")]/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))

        products = response.xpath('//div[@class="descr-title"]/a/@href').extract()
        products += response.xpath('//div[@class="hits-name"]/a/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product)

        pages = response.xpath('//a[@class="pagin-num"]/@href').extract()
        for url in pages:
            yield Request(response.urljoin(url))

    def parse_product(self, response):
        image_url = response.xpath('//div[contains(@class, "view-image")]/img/@src').extract()
        if not image_url:
            image_url = response.xpath('//div[@class="p_img"]/img/@src').extract()
        if not image_url:
            image_url = response.xpath('//div[@class="item-pic"]/img/@src').extract()
        product_identifier = response.xpath('//input[@id="product_id"]/@value').extract()
        if not product_identifier:
            product_identifier = re.findall('product/\?id=(.*)', response.url)

        if not product_identifier:
            log.msg('PRODUCT WITHOUT IDENTIFIER: ' + response.url)
            return

        sku = response.xpath('//div[contains(@class, "case-articul")]/text()').re(': (.*)')
        sku = sku[0] if sku else product_identifier
        price = response.xpath('//input[@id="oriPrice"]/@value').extract()
        if not price:
            price = '0'
        product_name = response.xpath('//h1/text()').extract()[0].strip()

        brand = response.xpath('//a[contains(@href, "producers[]")]/text()').extract()
        brand = brand[0] if brand else ''
        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('name', product_name)

        in_stock = response.xpath('//div[@class="case-pfix"]//span[@class="addBasket list"]/a')
        if not in_stock:
            product_loader.add_value('stock', 0)

        product_loader.add_value('sku', sku)
        if image_url:
            product_loader.add_value('image_url', response.urljoin(image_url[0]))
        product_loader.add_value('price', price)
        product_loader.add_value('url', response.url)
        product_loader.add_value('brand', brand)
        category = response.xpath('//a[@class="path-item"]/text()').extract()[-2]
        product_loader.add_value('category', category)
        product = product_loader.load_item()
        yield product

# -*- coding: utf-8 -*-
"""
Account: E-Bedding
Name: ebedding-matalan.co.uk
Ticket: https://www.assembla.com/spaces/competitormonitor/tickets/4956

Extract all products including options from the Bedroom category

"""

import re
from copy import deepcopy

from scrapy import Spider
from scrapy.http import Request, HtmlResponse

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader



class MatalanSpider(Spider):
    name = 'ebedding-matalan.co.uk'
    allowed_domains = ['matalan.co.uk']

    start_urls = ['http://www.matalan.co.uk/homeware/bedroom']

    def __init__(self, *args, **kwargs):
        super(MatalanSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        request = Request(self.start_urls[0], callback=self.parse_category)
        self._crawler.engine.crawl(request, self)

    def parse(self, response):
        categories = response.xpath('//header[@id="product-list-header"]//li/a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category), callback=self.parse_category)

    def parse_category(self, response):
        products = response.xpath('//ul[@id="products"]/li[contains(@class, "product")]//a[@class="link"]/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product, meta=response.meta)

        next = response.xpath('//li[@class="next"]/a/@href').extract()
        if next:
            yield Request(response.urljoin(next[0]), callback=self.parse_category)

    def parse_product(self, response):
 
        loader = ProductLoader(response=response, item=Product())
        identifier = re.findall('"id": "(.*)"', response.body)
        loader.add_value('identifier', identifier[0])
        loader.add_value('sku', identifier[0])
        loader.add_value('brand', '')
        categories = response.xpath('//ul[contains(@class, "breadcrumb")]/li/a//text()').extract()[1:]
        categories = filter(None, map(lambda x: x.strip(), categories))
        loader.add_value('category', categories)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        price = response.xpath('//div[@class="product-info-main"]//li[@class="price"]/text()').extract()
        price = price[0] if price else '0'
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        image_url = response.xpath('//section[@id="product-visuals"]//img[@itemprop="image"]/@src').extract()
        if image_url:
            image_url = image_url[0]
            if 'http' not in image_url:
                image_url = 'http:' + image_url
        else:
            image_url = ''
        loader.add_value('image_url', image_url)
        in_stock = response.xpath('//link[@itemprop="availability" and contains(@href, "InStock")]')
        if not in_stock:
            loader.add_value('stock', 0)

        item = loader.load_item()

        colours = response.xpath('//ul[@class="colors"]/li')        
        options = response.xpath('//select[@name="Size"]/option[@value!=""]')
        if options:
            for option in options:
                stock = int(option.xpath('@data-max').extract()[0])
                name = ''.join(option.xpath('text()').extract()).split(' - ')[0].strip()
                option_identifier = option.xpath('@value').extract()[0]
                option_item = deepcopy(item)
                if not stock:
                    option_item['stock'] = 0
                price = option.xpath('text()').re('Now (.*)')
                if not price:
                    price = option.xpath('text()').extract()
                option_item['price'] = extract_price(price[0])
                if option_item['price'] < 50:
                    option_item['shipping_cost'] = extract_price('3.95')

                if colours:
                    for colour in colours:
                        colour_name = colour.xpath('label/text()').extract()[0].strip()
                        colour_id = colour.xpath('input/@value').extract()[0]
                        option_item['name'] = option_item['name'] + ' ' + colour_name + ' ' + name
                        option_item['identifier'] = option_identifier+'-'+colour_id
                        option_item['sku'] = option_item['identifier']
                        yield option_item
                else:
                    option_item['name'] += ' ' + name
                    option_item['identifier'] = option_identifier
                    option_item['sku'] = option_item['identifier']
                    yield option_item
        else:
            if item['price'] < 50:
                item['shipping_cost'] = extract_price('3.95')
            if colours:
                for colour in colours:
                    option_item = deepcopy(item)
                    colour_name = colour.xpath('label/text()').extract()[0].strip()
                    colour_id = colour.xpath('input/@value').extract()[0]
                    option_item['name'] = option_item['name'] + ' ' + colour_name
                    option_item['identifier'] += '-' + colour_id
                    option_item['sku'] = option_item['identifier']
                    yield option_item
            else:
                yield item
                

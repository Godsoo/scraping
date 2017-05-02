# -*- coding: utf-8 -*-
"""
Account: BetterLife HealthCare
Name: betterlife_healthcare-careco.co.uk
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4678-betterlife-healthcare-|-careco-|-new-spider-build/details#
Original developer: Franco Almonacid <fmacr85@gmail.com>
"""

import re
from copy import deepcopy

from scrapy import Spider
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price


class CarecoSpider(Spider):
    name = u'betterlife_healthcare-careco.co.uk'
    allowed_domains = ['careco.co.uk']
    start_urls = ['http://www.careco.co.uk/']

    def parse(self, response):
        base_url = get_base_url(response)
        categories = response.xpath('//div[@id="menuBar"]//a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url))

        products = response.xpath('//div[@class="catProdTitle"]/a/@href').extract()
        if products:
            for url in products:
                yield Request(response.urljoin(url), callback=self.parse_product, meta={'categories': categories})

        pages = response.xpath('//div[@class="pagesWrapper"]/div[@class="pageCount"]/a/@href').extract()
        for page in pages:
            yield Request(response.urljoin(page))

        identifier = response.xpath('//div[@class="productCode"]/span/text()').extract()
        if identifier:
            for item in self.parse_product(response):
                yield item

    def parse_product(self, response):
        base_url = get_base_url(response)

        image_url = response.xpath('//img[@id="mainImg"]/@src').extract()

        product_loader = ProductLoader(item=Product(), response=response)
        identifier = response.xpath('//div[@class="productCode"]/span/text()').extract()
        if not identifier:
            return

        identifier = identifier[0]
        product_loader.add_value('identifier', identifier)
        product_loader.add_xpath('name', '//h1/text()')
        if image_url:
            product_loader.add_value('image_url', response.urljoin(image_url[0]))
        product_loader.add_value('sku', identifier)
        price = response.xpath('//div[@class="prodRightWrapper"]//div[@class="price"]/text()').extract()[0].strip()
        product_loader.add_value('price', price)
        product_loader.add_value('url', response.url)
        categories = response.xpath('//div[@id="breadCrumbWrapper"]//div[@itemprop="title"]/text()').extract()[1:-1]
        product_loader.add_value('category', categories)
        product_loader.add_value('brand', '')
        item = product_loader.load_item()

        options_url = "http://www.careco.co.uk/ajaxTwoDimSelect/"

        options = response.xpath('//select[@class="buysSelect"]/option[@value!=""]')
        if options:
            for option in options:
                option_item = deepcopy(item)
                name = option.xpath('text()').extract()[0].split(u'\xa3')[0].strip()
                option_item['name'] += ' ' + name
                identifier = option.xpath('@value').extract()[0]
                option_item['identifier'] += '-' + identifier
                price = option.xpath('text()').re(u'\xa3\d+\.\d+')
                if price:
                    option_item['price'] = extract_price(price[0])
                
                ajax_option = option.xpath('@onclick')
                if ajax_option:
                    formdata = {'FS': item['identifier'], 
                      	        'CODE': option.xpath('@value').extract()[0]}
                    yield FormRequest(options_url, dont_filter=True, formdata=formdata, callback=self.parse_options, meta={'item': option_item})
                else:
                    yield option_item
        else:
            yield item
        
    def parse_options(self, response):
        item = response.meta['item']

        options_url = "http://www.careco.co.uk/ajaxTwoDimSelect/"

        options = response.xpath('//select/option[@value!=""]')
        for option in options:
            option_item = deepcopy(item)
            name = option.xpath('text()').extract()[0].split(u'\xa3')[0].strip()
            option_item['name'] += ' ' + name
            identifier = option.xpath('@value').extract()[0]
            option_item['identifier'] += '-' + identifier
            price = option.xpath('text()').re(u'\xa3\d+\.\d+')
            if price:
                option_item['price'] = extract_price(price[0])
                
            ajax_option = option.xpath('@onclick')
            if ajax_option:
                formdata = {'FS': item['identifier'], 
                            'CODE': option.xpath('@value').extract()[0]}
                yield FormRequest(options_url, dont_filter=True, formdata=formdata, callback=self.parse_options, meta={'item': option_item})
            else:
                yield option_item

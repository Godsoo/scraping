# -*- coding: utf-8 -*-
"""
Account: E-Service UK
Name: eservices_uk-gadgetmonocle.com
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4612-e-services-uk---new-site---gadget-monocle/details#
Original developer: Franco Almonacid <fmacr85@gmail.com>
"""

import re
from scrapy import Spider
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price


class GadgetMonocleSpider(Spider):
    name = u'eservices_uk-gadgetmonocle.com'
    allowed_domains = ['gadgetmonocle.com']
    start_urls = ['http://www.gadgetmonocle.com/']

    def parse(self, response):
        base_url = get_base_url(response)
        categories = response.xpath('//ul[@id="mainNav"]//a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url))

        products = response.xpath('//article/a[@class="productWrapperLink"]/@href').extract()
        if products:
            categories = response.xpath('//nav[@id="breadcrumbs"]/a/text()').extract()[1:]
            categories.append(response.xpath('//nav[@id="breadcrumbs"]/span[@class="page-title"]/text()').extract()[-1].strip())
            for url in products:
                yield Request(response.urljoin(url), callback=self.parse_product, meta={'categories': categories})

        pages = response.xpath('//div[@id="pagination"]//a/@href').extract()
        for url in pages:
            yield Request(response.urljoin(url))

    def parse_product(self, response):
        base_url = get_base_url(response)

        image_url = response.xpath('//div[@id="productImages"]//img[@itemprop="image"]/@src').extract()

        product_loader = ProductLoader(item=Product(), response=response)
        identifier = re.findall('"rid":(.*)};', response.body)
        if not identifier:
            return

        identifier = identifier[0]
        product_loader.add_value('identifier', identifier)
        product_loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        if image_url:
            product_loader.add_value('image_url', 'http:' + image_url[0])
        product_loader.add_value('sku', identifier)
        price = response.xpath('//span[@id="productPrice"]/span/text()').extract()
        if not price:
            price = response.xpath('//meta[@property="og:price:amount"]/@content').extract()

        product_loader.add_value('price', price)
        product_loader.add_value('url', response.url)
        product_loader.add_value('category', response.meta['categories'])
        product_loader.add_xpath('brand', '//meta[@property="og:brand"]/@content')
        out_of_stock = response.xpath('//div[@id="productOptions"]/span[@class="sold-out"]')
        if out_of_stock:
            product_loader.add_value('stock', 0)
        product = product_loader.load_item()
        yield product

# -*- coding: utf-8 -*-
"""
Customer: Zyro
Website: http://www.freestylextreme.com
Extract all products on site including product options.

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4800

"""
import re

from scrapy.spider import BaseSpider

from scrapy.http import Request

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price

import itertools

from scrapy.utils.url import url_query_parameter


class FreestylExtremeSpider(BaseSpider):
    name = u'zyro-freestylextreme.com'
    allowed_domains = ['freestylextreme.com']
    start_urls = [
        'http://www.freestylextreme.com/uk/default.aspx?catid=5&lang=1'
    ]

    collected_identifiers = []

    def parse(self, response):

        categories = response.xpath('//ul[@id="mainNavigationUL"]//a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url))

        # products
        products = response.xpath('//div[contains(@class, "productGrid")]/a/@href').extract()
        for url in products:
            identifier = url_query_parameter(url.encode('utf'), 'prodid', '')
            if identifier and identifier not in self.collected_identifiers:
                self.collected_identifiers.append(identifier)
                yield Request(response.urljoin(url), callback=self.parse_product)

        # pagination
        next_page = response.xpath('//a[@id="pagerNext"]/@href').extract()
        if next_page:
            url = response.urljoin(next_page[0])
            yield Request(url)

    def parse_product(self, response):

        image_url = response.xpath('//a[@id="zoom"]/img/@src').extract()
        image_url = 'http:' + image_url[0] if image_url else ''

        product_identifier = re.findall("'id': '(\d+)'", response.body)
        if product_identifier:
            product_identifier = product_identifier[0]
        else:
            product_identifier = url_query_parameter(response.url.encode(utf), 'prodid', '')

        if not product_identifier:
            self.log("ERROR: No identifier found")
            return

        product_identifier = product_identifier
        sku = product_identifier
        product_name = response.xpath('//h1[@itemprop="name"]/text()').extract()[0].strip()
        categories = response.xpath('//span[@typeof="v:Breadcrumb"]/a/text()').extract()[1:-1]
        categories = map(lambda x: x.strip(), categories)
        brand = response.xpath('//span[@itemprop="brand"]/text()').extract()
        brand = brand[0].strip() if brand else ''
        product_price = response.xpath('//span[@class="product-cost-reduced"]/text()').extract()
        if not product_price:
            product_price = response.xpath('//meta[@itemprop="price"]/@content').extract()
        product_price = extract_price(product_price[0])

        options = response.xpath('//ul[@id="optionSelect"]//li/a[@id]')

        if options:
            for option in options:
                name = product_name + ' ' + option.xpath('span/text()').extract()[0]
                identifier = product_identifier
                option_id = option.xpath('@id').re('option-(\d+)')[0]
                identifier += '-' + option_id
                product_loader = ProductLoader(item=Product(), response=response)
                product_loader.add_value('identifier', identifier)
                product_loader.add_value('sku', identifier)

                out_of_stock = ''.join(response.xpath('//div[contains(@id, "'+option_id+'")]/p[strong[contains(text(), "Availability")]]/text()').extract()).strip().upper()
                out_of_stock = 'BACKORDER' in out_of_stock
                if out_of_stock:
                    product_loader.add_value('stock', 0)
                
                product_loader.add_value('name', name)
                if image_url:
                    product_loader.add_value('image_url', image_url)
                product_loader.add_value('price', product_price)
                if product_loader.get_output_value('price')<50:
                    product_loader.add_value('shipping_cost', 1.99)
                product_loader.add_value('url', response.url)
                product_loader.add_value('brand', brand)
                product_loader.add_value('category', categories)
                product = product_loader.load_item()
                yield product
        else:
            product_loader = ProductLoader(item=Product(), response=response)
            product_loader.add_value('identifier', product_identifier)
            out_of_stock = ''.join(response.xpath('//div[@id="delivery-first"]/p[strong[contains(text(), "Availability")]]/text()').extract()).strip().upper()
            out_of_stock = 'BACKORDER' in out_of_stock
            if out_of_stock:
                product_loader.add_value('stock', 0)

            product_loader.add_value('name', product_name)
            if image_url:
                product_loader.add_value('image_url', image_url)
            product_loader.add_value('price', product_price)
            if product_loader.get_output_value('price')<50:
                product_loader.add_value('shipping_cost', 1.99)
            product_loader.add_value('url', response.url)
            product_loader.add_value('brand', brand)
            product_loader.add_value('sku', sku)
            product_loader.add_value('category', categories)
            product = product_loader.load_item()
            yield product

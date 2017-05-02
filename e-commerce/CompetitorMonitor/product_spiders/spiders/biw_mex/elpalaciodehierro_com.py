# -*- coding: utf-8 -*-

import re
import json
from scrapy import Spider, Request
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from decimal import Decimal


class ElpalaciodehierroSpider(Spider):
    name = u'biw-mex-elpalaciodehierro.com'
    allowed_domains = ['elpalaciodehierro.com', 'xe.com']
    start_urls = ('http://www.elpalaciodehierro.com/', )

    def parse(self, response):
        for url in response.xpath('//ul[@class="level1"]//a/@href').extract():
            yield Request(
                response.urljoin(url),
                callback=self.parse_products_list
            )

    def parse_products_list(self, response):
        for url in response.xpath('//div[@class="widget widget-static-block"]//a/@href').extract():
            yield Request(
                response.urljoin(url),
                callback=self.parse_products_list
            )

        product_urls = response.xpath('//a[@class="product-image"]/@href').extract()
        for url in product_urls:
            yield Request(
                re.sub('\-\d\.htm', '.htm', response.urljoin(url)),
                callback=self.parse_product
            )

        for url in response.xpath('//div[@class="pages"]//a/@href').extract():
            yield Request(
                response.urljoin(url),
                callback=self.parse_products_list
            )

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        brand = map(unicode.strip, response.xpath('//div[@class="product-brand"]/*/text()').extract())
        brand = brand[0].strip() if brand else ''
        loader.add_value('brand', brand)
        name = response.xpath('//div[@class="product-name"]/span/text()').extract()[0].strip()
        price = response.xpath('//p[@class="special-price"]/span[2]/text()').extract()
        if not price:
            price = response.xpath('//span[@class="regular-price"]/span/text()').extract()
        if not price:
            price = response.xpath('//*[contains(@class, "price-info")]//span/text()').re(r'[\d.,]+')
        identifier = response.xpath('//script/text()').re("'prodIDsku':'(.+?)'")
        if identifier:
            identifier = identifier[0]
        else:
            identifier = response.xpath("//span[text()='sku']/../text()").re(': *(.+)')[0]
        loader.add_value('url', response.url)
        sku = response.xpath("//span[text()='sku']/../text()").re(': *(.+)')
        sku = sku[0] if sku else ''
        loader.add_value('sku', sku)
        category = response.xpath('//div[@class="breadcrumbs"]/ul/li/a/text()').extract()
        category = category[-1].strip() if category else ''
        loader.add_value('category', category)
        image_url = response.xpath('//*[@id="image"]/@src').extract()
        image_url = response.urljoin(image_url[0]) if image_url else ''
        loader.add_value('image_url', image_url)
        product = loader.load_item()
        price = extract_price(price[-1])

        if not response.xpath('//div[contains(@class, "options")]'):
            loader.add_value('name', name)
            loader.add_value('price', price)
            loader.add_value('identifier', identifier)
            url = 'http://www.xe.com/currencyconverter/convert/?Amount=%s&From=MXN&To=USD' %str(price)

            product = loader.load_item()
            yield Request(url, callback=self.convert, meta={'product':product}, dont_filter=True)
        else:
            options = re.search('var spConfig.*\((.*)\)', response.body)
            if options:
                options = json.loads(options.groups()[0])
                options = options['attributes'].values()[0]['options']
                for option in options:
                    option_name = '-'.join((name, option['label']))
                    option_id = '-'.join((identifier, option['id']))
                    url = 'http://www.xe.com/currencyconverter/convert/?Amount=%s&From=MXN&To=USD' %str(price)

                    yield Request(url, callback=self.convert, meta={'product':product, 'name': option_name, 'identifier': option_id}, dont_filter=True)

    @staticmethod
    def convert(response):
        product = response.meta['product']
        price = extract_price(response.xpath('//tr[@class="uccRes"]/td[@class="rightCol"]/text()').extract()[0])
        product['price'] = price.quantize(Decimal('1.00'))
        try:
            product['name'] = response.meta['name']
            product['identifier'] = response.meta['identifier']
        except:
            pass
        yield product

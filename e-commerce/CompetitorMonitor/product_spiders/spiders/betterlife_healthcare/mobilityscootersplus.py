# -*- coding: utf-8 -*-
import json
import itertools
from decimal import Decimal
from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class MobilityScootersPlus(CrawlSpider):
    name = 'betterlife_healthcare-mobilityscootersplus'
    allowed_domains = ['mobilityscootersplus.com']
    start_urls = ['http://www.mobilityscootersplus.com/']
    
    categories = LinkExtractor(restrict_css='ul#nav')
    pages = LinkExtractor(restrict_css='div.pages')
    products = LinkExtractor(restrict_css='ul.products-grid')
    
    rules = (Rule(categories),
             Rule(pages),
             Rule(products, callback='parse_product'))

    def parse_product(self, response):
        options_selects = response.css('label.required').xpath('../following-sibling::dd[1]').css('div.input-box').xpath('*[1]')
        options_config = response.xpath('//script/text()').re_first('Product.Config.*?({.+})')
        if not options_selects:
            for item in self.parse_simple_product(response):
                yield item
            return

        options = []
        for option in options_selects:
            if option.extract().startswith('<select'):
                if option.xpath('option[@value!=""]'):
                    options.append(option.xpath('option[@value!=""]'))
            else:
                options.append(option.xpath('li'))
                
        if options_config:
            items = self.parse_product_options_config(response)
        else:
            items = self.parse_simple_product(response)

        for item in items:
            if not options:
                yield item
                continue
            
            variants = itertools.product(*options)
            for variant in variants:
                loader = ProductLoader(Product(), response=response)
                loader.add_value(None, item)
                identifier = item['identifier'] + '-' + '-'.join((option.xpath('.//@value').extract_first() for option in variant))
                loader.replace_value('identifier', identifier)
                loader.replace_value('sku', identifier)
                price = item['price']
                for option in variant:
                    name = option.xpath('text()').extract_first() or option.xpath('.//label/text()').extract_first()
                    name = name.split(u'+£')[0]
                    loader.add_value('name', name)
                    price += Decimal(option.xpath('.//@price').extract_first())
                loader.replace_value('price', price)
                yield loader.load_item()
        
    def parse_simple_product(self, response):
        loader = ProductLoader(Product(), response=response)
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_value('url', response.url)
        loader.add_css('name', 'div.product-name h1::text')
        loader.add_css('price', 'li.bigPrice span.price::text')
        loader.add_xpath('sku',  '//input[@name="product"]/@value')
        category = response.css('div.breadcrumbs a::text').extract()[1:]
        loader.add_value('category', category)
        loader.add_css('image_url', 'img#image::attr(src)')
        item = loader.load_item()
        yield item
        
    def parse_product_options_config(self, response):
        options = response.xpath('//script/text()').re_first('Product.Config.*?({.+})')
        loader = ProductLoader(Product(), response=response)
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_value('url', response.url)
        loader.add_css('name', 'div.product-name h1::text')
        loader.add_css('price', 'li.bigPrice span.price::text')
        loader.add_xpath('sku',  '//input[@name="product"]/@value')
        category = response.css('div.breadcrumbs a::text').extract()[1:]
        loader.add_value('category', category)
        loader.add_css('image_url', 'img#image::attr(src)')
        item = loader.load_item()
        if not options:
            yield item
            return
        
        options = json.loads(options)
        attributes = sorted(options['attributes'].values())
        products = [option['products'] for attr in attributes for option in attr['options']]
        products = set(itertools.chain(*products))
        for product in products:
            loader = ProductLoader(Product(), response=response)
            loader.add_value(None, item)
            identifier = item['identifier'] + '-' + product
            loader.replace_value('identifier', identifier)
            loader.replace_value('sku', identifier)
            options = [option for attr in attributes for option in attr['options'] if product in option['products']]
            price = item['price']
            for option in options:
                loader.add_value('name', option['label'])
                price += Decimal(option['price'])
            loader.replace_value('price', price)
            yield loader.load_item()
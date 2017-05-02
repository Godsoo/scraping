# -*- coding: utf-8 -*-

import re
import os
import json
import itertools
from copy import deepcopy
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest

from scrapy.item import Item, Field

from scrapy import log

from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.utils import extract_price
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)


HERE = os.path.abspath(os.path.dirname(__file__))

class MetaData(Item):
    Promotions = Field()

class BetterBathroomsSpider(BaseSpider):
    name = "bathempire-betterbathrooms.com"
    allowed_domains = ["betterbathrooms.com"]
    start_urls = ['http://www.betterbathrooms.com']
    user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:40.0) Gecko/20100101 Firefox/40.0'

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response=response)

	categories = hxs.select('//nav[@class="top-nav-container"]//a/@href').extract()
        categories += hxs.select('//div[@class="categories-list"]//li[@class="item"]/a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

        products = hxs.select('//div[@class="category-products"]//li[contains(@class, "item")]/a/@href').extract()
        
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        next = hxs.select('//a[@class="next i-next"]/@href').extract()
        if next:
            yield Request(urljoin_rfc(response.url, next[0]))

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response=response)

        name = hxs.select('//h1/span[@itemprop="name"]/text()').extract()[0]
      
        price = ''.join(''.join(hxs.select('//form//p[@class="special-price"]//span[@class="price"]/text()').extract()).split())
        if not price:
            price = ''.join(''.join(hxs.select('//span[@class="regular-price"]//span[@class="price"]/text()').extract()).split())
        price = extract_price(price)

        brand = ''
        categories = hxs.select('//div[@itemprop="breadcrumb"]/a/text()').extract()[1:]

        l = ProductLoader(item=Product(), response=response)

        image_url = hxs.select('//ul[@id="product-img-main"]//img/@src').extract()
        image_url = image_url[0] if image_url else ''

        l.add_value('image_url', image_url)
        l.add_value('url', response.url)
        l.add_value('name', name)
        l.add_value('price', price)
        l.add_value('brand', brand)
        l.add_value('category', categories)
        sku = hxs.select('//span[@itemprop="sku"]/text()').extract()
        sku = sku[0] if sku else ''
        l.add_value('sku', sku)

        identifier = hxs.select('//input[@name="product"]/@value').extract()
        l.add_value('identifier', identifier[0])

        item = l.load_item()

        promotions = hxs.select('//div[@class="bb-price-group" and //span[contains(text(), "Was")]]//span/text()').extract()

        metadata = MetaData()
        metadata['Promotions'] = ' '.join(promotions) if promotions else ''
        item['metadata'] = metadata
 
        available_options = hxs.select('//select[contains(@name, "bundle_option")]/option[not(@value="")]/@value').extract()
        if not available_options:
            available_options = hxs.select('//input[contains(@id, "bundle-option") and not(@value="0" or @value="1")]/@value').extract()

        options_bundle = re.search(r'new Product.Bundle\((.*)\)', response.body)
        if options_bundle and available_options:
            log.msg('OPTION BUNDLE: ' + response.url)
            combined_options = []
            product_data = json.loads(options_bundle.groups()[0])
            for id, options in product_data['options'].iteritems():
                element_options = []
                for option_id, option in options['selections'].iteritems():
                    if option_id not in available_options:
                        continue

                    option_name = hxs.select('//option[@value="'+option_id+'"]/text()').extract()
                    if not option_name:
                        option_name = hxs.select('//li[input[@value="'+option_id+'"]]//label/text()').extract()
                    option_name = option_name[0].split(u'\xa0')[0].strip()

                    option_price = option['priceInclTax']
                    option_attr = (option_id, option_name, option_price)
                    element_options.append(option_attr)
                combined_options.append(element_options)

            combined_options = [combined_option for combined_option in combined_options if combined_option]
            combined_options = list(itertools.product(*combined_options))
            options = []
            for combined_option in combined_options:
                final_option = {}
                for option in combined_option:
                    final_option['desc'] = final_option.get('desc', '') + ' ' + option[1]
                    final_option['identifier'] = final_option.get('identifier', '') + '-' + option[0]
                    final_option['price'] = final_option.get('price', 0) + option[2]
                options.append(final_option)

            for option in options:
                option_item = deepcopy(item)
                option_item['identifier'] += option['identifier']
                option_item['name'] += option['desc']
                option_item['price'] += extract_price(str(option['price']))

                yield option_item
        else:
            options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
            if options_config:
                product_data = json.loads(options_config.groups()[0])
                products = {}
                prices = {}
                for attr in product_data['attributes'].itervalues():
                    for option in attr['options']:
                        for product in option['products']:
                            products[product] = ' - '.join((products.get(product, ''), option['label']))
                            price = option.get('price') if option.get('price', 0) else option.get('oldPrice')
                            prices[product] = prices.get(product, 0) +  extract_price(price)

                for option_identifier, option_name in products.iteritems():
                    option_item = deepcopy(item)

                    option_item['identifier'] += '-' + option_identifier
                    option_item['name'] += option_name
                    option_item['price'] = extract_price(product_data['childProducts'][option_identifier]['finalPrice'])

                    yield option_item
            else:
                yield item


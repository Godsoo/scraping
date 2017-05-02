# -*- coding: utf-8 -*-
"""
Account: Kitbag AU
Name: kitbag_au-subside.com.au
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5046

Extract all products from these categories: http://screencast.com/t/aXxBTQL614
Extract all product options.

The spiders adds the player names and numbers as metadata.
(copied from Kitbag UK)

"""

import re
import json
import itertools
from hashlib import md5
from copy import deepcopy
from scrapy.spider import Spider
from scrapy.http import Request
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price


class SubsideSpider(Spider):
    name = u'kitbag_au-subside.com.au'
    allowed_domains = ['subside.com.au']
    start_urls = ['http://www.subside.com.au/products/clothing/soccer-jerseys',
                  'http://www.subside.com.au/products/clothing/soccer-shorts',
                  'http://www.subside.com.au/products/clothing/socks',
                  'http://www.subside.com.au/products/accessories/soccer-balls']

    def add_identifier_and_return(self, item):
        try:
            item['identifier'] = md5(item['name'].lower()).hexdigest()
        except UnicodeEncodeError:
            item['identifier'] = md5(name.lower().encode('utf-8')).hexdigest()
        return item

    def parse(self, response):
        products = response.xpath('//li[contains(@class,"item")]//h2[@class="product-name"]/a/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product)

        next_page = response.xpath('//li[@class="next"]/a/@href').extract()
        if next_page:
            yield Request(next_page[0])

    def parse_product(self, response):
        name = response.xpath('//div[@class="product-name"]/h1/text()').extract()[0].strip()
        brand = response.xpath('//div[@class="box-brand"]/a/img/@alt').extract()
        brand = brand[0].split(',')[0] if brand else ''
        image_url = response.xpath('//img[@id="image-main"]/@src').extract()
        price = response.xpath('//p[@class="special-price"]/span[@class="price"]/text()').extract()
        if not price:
            price = response.xpath('//span[@class="regular-price"]/span[@class="price"]/text()').extract()
        categories = response.xpath('//div[@class="breadcrumbs"]//span/text()').extract()[1:-1]

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        if image_url:
            loader.add_value('image_url', image_url[0])
        loader.add_value('price', extract_price(price[0]))
        loader.add_value('category', categories)
        loader.add_xpath('sku', '//div[@class="sku"]/span[@class="value"]/text()')
        loader.add_value('brand', brand)
        loader.add_value('shipping_cost', '14.95')

        stock = response.xpath('//p[@class="availability in-stock"]')
        if not stock:
            loader.add_value('stock', 0)

        item = loader.load_item()

        item['metadata'] = {}

        yield self.add_identifier_and_return(item)


        options_containers = response.xpath('//div[@class="option" and .//dt/label[contains(text(), "Official Key Player")]]//select[contains(@name, "options[")]')
        options_containers += response.xpath('//div[@class="option" and .//dt/label[contains(text(), "Match Transfer")]]//select[contains(@name, "options[")]')
        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            for attr in product_data['attributes'].itervalues():
                is_size = attr['code'] == 'size'
                for option in attr['options']:
                    for product in option['products']:
                        if product not in products:
                            products[product] = {
                                'name': ' '.join((products.get(product, ''), option['label'])),
                                'size': option['label'] if is_size else None,
                                'price': extract_price(option['price']),
                            }

            if not options_containers:
                for option_identifier, option_attrs in products.iteritems():
                    product_option = deepcopy(item)
                    product_option['name'] += option_attrs['name']
                    product_option['price'] = extract_price(str(product_option['price'])) + option_attrs['price']
                    product_option['metadata'] = {'size': option_attrs['size']}
                    yield self.add_identifier_and_return(product_option)


        if options_containers:
            players = {}
            player_options = response.xpath('//div[@class="option" and .//dt/label[contains(text(), "Official Key Player")]]//select[contains(@name, "options[")]/option[@value!=""]')
            for player_option in player_options:
                player_name = player_option.xpath('text()').re('(.*) \d+')
                player_number = player_option.xpath('text()').re(' (\d+)')
                option_name = player_option.xpath('text()').extract_first().split('+$')[0]
                option_id = player_option.xpath('@value').extract()[0]
                if player_name and player_number:
                    players[option_id] = {'name': player_name[0],
                                          'number': player_number[0],
                                          'option_name': option_name}

            combined_options = []
            for options_container in options_containers:
                element_options = []
                for option in options_container.xpath('option'):
                    option_id = option.xpath('@value').extract()[0]
                    if option_id:
                        option_name = option.xpath('text()').extract()[0].split(' (+')[0]
                        option_name = option_name.split('+')[0].strip()
                    else:
                        option_name = ''
                        option_id = options_container.xpath('@id').re('select_(\d+)')[0] + '_'
                    option_price = option.re(r'([\d\.,]+)\sInc')
                    if not option_price:
                        option_price = option.re(r'\+..([\d\.,]+)')
                    option_price = option_price[0] if option_price else '0'

                    option_attr = (option_id, option_name, option_price)
                    element_options.append(option_attr)
                combined_options.append(element_options)

            combined_options = list(itertools.product(*combined_options))
            options = []
            for combined_option in combined_options:
                final_option = {}
                for option in combined_option:
                    final_option['desc'] = (final_option.get('desc', '') + ' ' + option[1]).strip()
                    final_option['price'] = final_option.get('price', 0) + extract_price(option[2])
                    player = players.get(option[0], None)
                    if player:
                        final_option['player'] = player
                options.append(final_option)

            for option in options:
                product_option = deepcopy(item)
                loader = ProductLoader(response=response, item=Product())
                option_name = option['desc']
                if option_name:
                    product_option['name'] += ' ' + option_name
                product_option['price'] = extract_price(str(product_option['price'])) + option['price']

                if option.get('player', None):
                    product_option['metadata']['player'] = option['player']['name']
                    product_option['metadata']['number'] = option['player']['number']

                if options_config and products:
                    for option_identifier, option_attr in products.iteritems():
                        final_option = deepcopy(product_option)
                        final_option['name'] += option_attr['name']
                        final_option['price'] = extract_price(str(final_option['price'])) + option_attr['price']
                        final_option['metadata']['size'] = option_attr['size']
                        yield self.add_identifier_and_return(final_option)
                else:
                    yield self.add_identifier_and_return(product_option)

        else:
            if not options_config:
                yield self.add_identifier_and_return(item)

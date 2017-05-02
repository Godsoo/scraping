# -*- coding: utf-8 -*-
"""
Account: Kitbag
Name: kitbag-subsidesports.com
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/4923

Extract all products from these categories: http://screencast.com/t/aXxBTQL614
Extract all product options.

The spiders adds the player names and numbers as metadata.

"""

import re
import json
import itertools
from collections import defaultdict
from copy import deepcopy
from scrapy.spider import BaseSpider
from scrapy.http import Request
from product_spiders.utils import remove_accent_mark
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price


PLAYERS = {
    'ALEXIS': '17',
    'AUBAMEYANG': '17',
    'BRAVO': '13',
    'BROWN': '8',
    'COURTOIS': '13',
    'COUTINHO': '10',
    'DE GEA': '1',
    'FABREGAS': '10',
    'GERRARD': '8',
    'GRIFFITHS': '9',
    'HART': '1',
    'HAZARD': '10',
    'IBRAHIMOVIC': '10',
    'ICARDI': '9',
    'INIESTA': '6',
    'KAKA': '10',
    'KANE': '10',
    'AGÜERO': '10',
    'LAMPARD': '8',
    'LEWANDOWSKI': '9',
    'LUKAKU': '10',
    'MENEZ': '7',
    'MESSI': '10',
    'MIGNOLET': '22',
    'MULLER': '25',
    'NAVAS': '1',
    'OZIL': '8',
    'PIRLO': '21',
    'POGBA': '19',
    'RONALDO': '7',
    'ROONEY': '10',
    'TOTTI': '10',
    'TURAN': '10',
    'WILLIAMS': '10'}


class SubsideSportsSpider(BaseSpider):
    name = u'kitbag-subsidesports.com'
    allowed_domains = ['www.subsidesports.com']
    start_urls = ['http://www.subsidesports.com/uk/products/clothing/football-shirts',
                  'http://www.subsidesports.com/uk/products/clothing/football-shorts',
                  'http://www.subsidesports.com/uk/products/clothing/socks',
                  'http://www.subsidesports.com/uk/products/accessories/soccer-balls']
    collected_identifiers = defaultdict(int)

    def _get_player_number(self, product_name):
        product_name = remove_accent_mark(product_name)
        for player, number in PLAYERS.items():
            if player.decode('utf-8').lower() in product_name.decode('utf-8').lower() and number.decode('utf-8') in product_name.decode('utf-8'):
                return player, number
        return '', ''

    def parse(self, response):

        products = response.xpath('//li[contains(@class,"item")]//h2[@class="product-name"]/a/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product)

        next = response.xpath('//li[@class="next"]/a/@href').extract()
        if next:
            yield Request(next[0])

    def parse_product(self, response):

        name = response.xpath('//div[@class="product-name"]/h1/text()').extract()[0].strip()
        brand = response.xpath('//div[@class="box-brand"]/a/img/@alt').extract()
        brand = brand[0].split(',')[0] if brand else ''
        image_url = response.xpath('//img[@id="image-main"]/@src').extract()
        price = response.xpath('//span[@class="price-including-tax"]/span[@class="price"]/text()').extract()
        identifier = response.xpath('//input[@name="product"]/@value').extract()[0]
        categories = response.xpath('//div[@class="breadcrumbs"]//span/text()').extract()[1:-1]

        player, number = self._get_player_number(name)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        if image_url:
            loader.add_value('image_url', image_url[0])
        loader.add_value('price', extract_price(price[0]))
        loader.add_value('category', categories)
        loader.add_value('identifier', identifier)
        loader.add_xpath('sku', '//div[@class="sku"]/span[@class="value"]/text()')
        loader.add_value('brand', brand)
        loader.add_value('shipping_cost', 3.75)

        stock = response.xpath('//p[@class="availability in-stock"]')
        if not stock:
            loader.add_value('stock', 0)

        item = loader.load_item()

        item['metadata'] = {}
        if player and number:
            item['metadata']['player'] = player
            item['metadata']['number'] = number
        self.collected_identifiers[item['identifier']] += 1
        yield item


        options_containers = response.xpath('//div[@class="option" and .//dt/label[contains(text(), "Official Key Player")]]//select[contains(@name, "options[")]')
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

            for option_identifier, option_attrs in products.iteritems():
                product_option = deepcopy(item)
                product_option['identifier'] += '-' + option_identifier
                product_option['name'] += option_attrs['name']
                product_option['price'] = extract_price(str(product_option['price'])) + option_attrs['price']
                product_option['metadata'] = {'player': player,
                                              'number': number,
                                              'size': option_attrs['size']}
                self.collected_identifiers[product_option['identifier']] += 1
                yield product_option


        if options_containers:

            players = {}
            player_options = response.xpath('//div[@class="option" and .//dt/label[contains(text(), "Official Key Player")]]//select[contains(@name, "options[")]/option[@value!=""]')
            for player_option in player_options:
                player_name = player_option.xpath('text()').re('(.*) \d+')
                player_number = player_option.xpath('text()').re(' (\d+)')
                option_id = player_option.xpath('@value').extract()[0]
                if player_name and player_number:
                    players[option_id] = {'name': player_name[0], 'number': player_number[0]}

            combined_options = []
            for options_container in options_containers:
                element_options = []
                for option in options_container.xpath('option[@value!=""]'):
                    option_id = option.xpath('@value').extract()[0]
                    option_name = option.xpath('text()').extract()[0].split(' (+')[0]
                    option_name = option_name.split('+')[0]
                    option_price = option.re(r'([\d\.,]+)\sInc')
                    if not option_price:
                        option_price = option.re(r'\+.([\d\.,]+)')
                    option_price = option_price[0] if option_price else '0'

                    option_attr = (option_id, option_name, option_price)
                    element_options.append(option_attr)
                combined_options.append(element_options)

            combined_options = list(itertools.product(*combined_options))
            options = []
            for combined_option in combined_options:
                final_option = {}
                for option in combined_option:
                    final_option['desc'] = final_option.get('desc', '') + ' ' + option[1]
                    final_option['identifier'] = final_option.get('identifier', '') + '-' + option[0]
                    final_option['price'] = final_option.get('price', 0) + extract_price(option[2])
                    player = players.get(option[0], None)
                    if player:
                        final_option['player'] = player
                    final_option['price']
                options.append(final_option)

            for i, option in enumerate(options, 1):
                product_option = deepcopy(item)
                loader = ProductLoader(response=response, item=Product())
                if 'player' in option:
                    product_option['identifier'] += '-' + option['player']['name'] +'-'+ option['player']['number']
                else:
                    product_option['identifier'] = product_option['identifier'] + option['identifier']
                product_option['name'] += ' ' + option['desc']
                product_option['price'] = extract_price(str(product_option['price'])) + option['price']

                if 'player' in option:
                    product_option['metadata']['player'] = option['player']['name']
                    product_option['metadata']['number'] = option['player']['number']

                if options_config and products:
                    for option_identifier, option_attr in products.iteritems():
                        final_option = deepcopy(product_option)
                        final_option['identifier'] += '-' + option_identifier
                        final_option['name'] += option_attr['name']
                        final_option['price'] = extract_price(str(final_option['price'])) + option_attr['price']
                        final_option['metadata']['size'] = option_attr['size']
                        if final_option['identifier'] in self.collected_identifiers:
                            final_option['identifier'] += '-' + str(self.collected_identifiers[final_option['identifier']])
                        self.collected_identifiers[final_option['identifier']] += 1
                        yield final_option
                else:
                    if product_option['identifier'] in self.collected_identifiers:
                        product_option['identifier'] += '-' + str(self.collected_identifiers[product_option['identifier']])
                    self.collected_identifiers[product_option['identifier']] += 1
                    yield product_option

        else:
            if not options_config:
                yield item

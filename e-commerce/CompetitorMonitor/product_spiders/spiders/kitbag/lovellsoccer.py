# -*- coding: utf-8 -*-
"""
Account: Kitbag
Name: kitbag-lovellsoccer.co.uk
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/4922
Extract all products from the "Football Shirts" category: http://screencast.com/t/pfMVU1AxQ9 and also from http://www.lovellsoccer.co.uk/Football-Boots and http://www.lovellsoccer.co.uk/Football-Boots categories

If the product allows to add personalization, the spider checks the team in the flat file and
assigns all the players and with his number as a product options

The spiders adds the player names and numbers as metadata.

"""
import os
import re
import csv
from decimal import Decimal

from copy import deepcopy
from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))


class LovellSoccerSpider(BaseSpider):
    name = u'kitbag-lovellsoccer.co.uk'
    allowed_domains = ['www.lovellsoccer.co.uk']
    start_urls = ('http://www.lovellsoccer.co.uk/Football-Replica-Shirts',
                  'http://www.lovellsoccer.co.uk/Football-Boots',
                  'http://www.lovellsoccer.co.uk/shop/Group/Coaching/Type/Match-Footballs',
                  'http://www.lovellsoccer.co.uk/shop/Group/Coaching/Type/Training-Footballs'
                  )

    teams = {}
    free_delivery_over = Decimal('100.00')

    def __init__(self, *args, **kwargs):
        super(LovellSoccerSpider, self).__init__(*args, **kwargs)

        teams_file = os.path.join(HERE, 'teams.csv')
        with open(teams_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                team = row['Merret Department'].strip().upper()
                player_name = row['HERO NAME'].strip()
                number = row['HERO NUMBER'].strip()

                player_id = player_name+'-'+number
                if self.teams.get(team):
                    if player_name!='N/A':
                        self.teams[team][player_id] = {'name': player_name,
                                                                'number': number}
                else:
                    if player_name!='N/A':
                        self.teams[team] = {player_id: {'name': player_name,
                                                                 'number': number}}

    def start_requests(self):
        menu_url = 'http://www.lovellsoccer.co.uk/CQ-116-5-15-19-1/scripts-auto/LS-en-GB-megaMenuArrays-responsive.js'
        yield Request(menu_url, callback=self.parse_menu)

        for url in self.start_urls:
            yield Request(url)

    def parse_menu(self, response):
        base_url = "http://www.lovellsoccer.co.uk"

        main_category = re.findall('All Football Shirts(.*)', response.body)
        if main_category:
            urls = re.findall(":(.*?)'", main_category[0])
            for url in urls:
                if '/' in url:
                    yield Request(urljoin_rfc(base_url, url))

    def parse(self, response):
        base_url = "http://www.lovellsoccer.co.uk"

        categories = response.xpath('//div[contains(@class, "block4col")]/a/@href').extract()
        categories += response.xpath('//span[@class="link"]/a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))

        products = []
        for line in response.body.split('\n'):
            if line.strip().startswith('pD['):
                products.append(line.split('~')[1])

        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)


    def parse_product(self, response):

        loader = ProductLoader(item=Product(), response=response)
        name = response.xpath('//h1[@class="product-name"]/text()').extract()[0].strip()
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        image_url = response.xpath('//img[@id="mainpic"]/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])
        price = response.xpath('//div[@class="product-cost"]/span[@class="price-main special"]/text()').extract()
        if not price:
            price = response.xpath('//div[@class="product-cost"]/div[@class="price-main"]/text()').extract()
        loader.add_value('price', extract_price(price[0]))
        categories = response.xpath('//div[@id="breadCrumbs"]//a/text()').extract()[1:]
        loader.add_value('category', categories)

        sku = response.xpath('//div[@class="product-id"]/text()').re('Product code: (.*)')[0]
        loader.add_value('identifier', sku)
        loader.add_value('sku', sku)
        brand = response.xpath('//h3/text()').extract()
        brand = brand[0].split(',')[0] if brand else ''
        loader.add_value('brand', brand)
        if price and extract_price(price[0]) < self.free_delivery_over:
            loader.add_value('shipping_cost', 3.49)

        item = loader.load_item()

        addition_price_shirt = response.xpath('//div[contains(@class, "personalisation-form shirts")]/h4/text()').re('\d+.\d+')

        options = response.xpath('//div[@id="select-item-size-buttons"]/div[contains(@class, "orderButtonDiv")]')
        if options:
            for option in options:
                option_item = deepcopy(item)
                size = option.xpath('a/span/text()').extract()[0]
                option_item['identifier'] += '-' + size
                option_item['name'] += ' ' + size
                in_stock = option.xpath('a[contains(@onclick, "In Stock")]').extract()
                if not in_stock:
                    option_item['stock'] = 0
                if addition_price_shirt:
                    add_price = extract_price(addition_price_shirt[0])
                    for team, players in self.teams.iteritems():
                        product_name = option_item['name'].upper()
                        if team.upper() in product_name or product_name.split()[0] == team.upper():
                            for player_id, player in players.iteritems():
                                player_item = deepcopy(option_item)
                                player_item['identifier'] += '-' + player_id.decode('utf')
                                player_item['name'] += u' ' + player['name'].decode('utf') + ' ' + player['number']
                                player_item['price'] += add_price
                                if player_item['price'] >= self.free_delivery_over:
                                    player_item['shipping_cost'] = '0.00'
                                else:
                                    player_item['shipping_cost'] = '3.49'
                                metadata = {'size': size}
                                metadata['player'] = player['name'].decode('utf')
                                metadata['number'] = player['number']
                                player_item['metadata'] = metadata
                                yield player_item
                option_item['metadata'] = {'size': size}
                yield option_item
        else:
            yield item

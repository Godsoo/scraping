# -*- coding: utf-8 -*-
"""
Account: Kitbag
Name: kitbag-jdsports.co.uk
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/4921
Extract all products from the "Football" main category: http://screencast.com/t/PjB4d1fgdkIX

If the product allows to add personalization, the spider checks the team in the flat file and
assigns all the players and with his number as a product options

The spiders adds the player names and numbers as metadata.

"""
import re
import os
import csv
from decimal import Decimal

from copy import deepcopy
from scrapy.spider import BaseSpider
from scrapy.http import Request
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price


HERE = os.path.abspath(os.path.dirname(__file__))


class JDSportsSpider(BaseSpider):
    name = u'kitbag-jdsports.co.uk'
    allowed_domains = ['www.jdsports.co.uk']
    start_urls = ['http://www.jdsports.co.uk/page/football/',
                  'http://www.jdsports.co.uk/men/mens-footwear/football-boots/',
                  'http://www.jdsports.co.uk/featured/Footballs/?facet%3Aproduct-type-jd=footballs&q=0'
                  ]

    teams = {}
    free_delivery_over = Decimal('60.0')

    def __init__(self, *args, **kwargs):
        super(JDSportsSpider, self).__init__(*args, **kwargs)

        teams_file = os.path.join(HERE, 'teams.csv')
        with open(teams_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                team = row['Merret Department'].strip().upper()
                player_name = row['HERO NAME'].strip()
                number = row['HERO NUMBER'].strip()
                if self.teams.get(team):
                    if player_name!='N/A':
                        self.teams[team][player_name+number] = {'name': player_name,
                                                                'number': number}
                else:
                    if player_name!='N/A':
                        self.teams[team] = {player_name+number: {'name': player_name,
                                                                 'number': number}}

    def parse(self, response):
        categories = response.xpath('//li[a[@data-ip-position="football-hover-menu"]]//a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))

        products = response.xpath('//ul[contains(@class,"listProducts")]//a[@class="itemView"]/@href').extract()
        products += response.xpath('//ul[contains(@class,"listProducts")]//span[@class="itemTitle"]//a/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product)

        next_page = response.xpath('//a[@title="Next Page"]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]))

    def parse_product(self, response):

        loader = ProductLoader(item=Product(), response=response)
        name = response.xpath('//h1[@itemprop="name"]/text()').extract()[0].strip()
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        image_url = response.xpath('//meta[@property="og:image"]/@content').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])
        price = response.xpath('//div[@class="itemPrices"]/span[@class="pri"]/span[@itemprop="price"]/text()').extract()
        if not price:
            price = response.xpath('//div[@class="itemPrices"]/span[@itemprop="price"]/text()').extract()
        loader.add_value('price', extract_price(price[0]))
        categories = response.xpath('//div[@id="breads"]//span[@itemprop="itemListElement"]/a/span/text()').extract()[1:]
        loader.add_value('category', categories)

        sku = response.xpath('//input[@name="productSku"]/@value').extract()[0]
        loader.add_value('identifier', sku)
        loader.add_value('sku', sku)
        brand = re.findall('brand: "(.*)"', response.body)
        brand = brand[0].title() if brand else ''
        loader.add_value('brand', brand)
        if price and extract_price(price[0]) < self.free_delivery_over:
            loader.add_value('shipping_cost', 3.99)

        item = loader.load_item()

        addition_price_shirt = response.xpath('//div[@class="itemCharacters shirt"]/input/@data-group-price').extract()

        options = response.xpath('//div[@class="options"]/button')
        if options:
            for option in options:
                option_item = deepcopy(item)
                size = option.xpath('text()').extract()[0].strip()
                option_item['identifier'] = option.xpath('@data-sku').extract()[0]
                option_item['name'] += ' ' + option.xpath('text()').extract()[0].strip()
                option_item['price'] = extract_price(option.xpath('@data-price').extract()[0])
                out_of_stock = 'nostock' in option.xpath('@class').extract()[0].lower()
                if out_of_stock:
                    option_item['stock'] = 0
                option_item['metadata'] = {'size': size}
                if addition_price_shirt:
                    add_price = extract_price(addition_price_shirt[0])
                    for team, players in self.teams.iteritems():
                        product_name = option_item['name'].upper()
                        if team.upper() in product_name or product_name.split()[0] == team.upper():
                            for player_id, player in players.iteritems():
                                player_item = deepcopy(option_item)
                                player_item['identifier'] += u'-' + player_id.decode('utf')
                                player_item['name'] += u' ' + player['name'].decode('utf') + ' ' + player['number']
                                player_item['price'] += add_price
                                if price and player_item['price'] >= self.free_delivery_over:
                                    player_item['shipping_cost'] = '0.00'
                                else:
                                    player_item['shipping_cost'] = '3.99'
                                player_item['metadata']['player'] = player['name'].decode('utf')
                                player_item['metadata']['number'] = player['number']
                                yield player_item
                yield option_item
        else:
            yield item

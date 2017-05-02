"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4975

The spider crawls Jerseys category
Collects all options.
"""
import scrapy
import csv
import os
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from kitbagitems import KitBagMeta
from scrapy.utils.url import add_or_replace_parameter
import re

HERE = os.path.abspath(os.path.dirname(__file__))

class SoccercornerSpider(scrapy.Spider):
    name = 'kitbag-soccercorner.com'
    allowed_domains = ['soccercorner.com']
    start_urls = ('http://www.soccercorner.com/Soccer-Jerseys-s/9.htm?searching=Y&sort=3&cat=9&show=300&page=1',)
    teams = {}

    def __init__(self, *args, **kwargs):
        super(SoccercornerSpider, self).__init__(*args, **kwargs)

        teams_file = os.path.join(HERE, 'teams.csv')
        with open(teams_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                team = row['Merret Department'].strip().upper()
                player_name = row['HERO NAME'].strip()
                number = row['HERO NUMBER'].strip()
                if self.teams.get(team):
                    if player_name != 'N/A':
                        self.teams[team][player_name + number] = {'name': player_name,
                                                                  'number': number}
                else:
                    if player_name != 'N/A':
                        self.teams[team] = {player_name + number: {'name': player_name,
                                                                   'number': number}}

    def parse(self, response):
        for url in response.xpath('//table[@class="v65-productDisplay"]//td/a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product)

        for page in response.xpath('//div[@class="pages_available_text"]/a/text()').extract():
            url = add_or_replace_parameter(response.url, 'page', page)
            yield scrapy.Request(response.urljoin(url), callback=self.parse)

    def parse_product(self, response):
        if 'Product price is not filled in. This product cannot be purchased.' in response.body:
            return
        identifier = response.xpath('//input[@name="ProductCode"]/@value').extract_first()
        name = response.xpath('//span[@itemprop="name"]/text()').extract_first()
        stock =response.xpath('//meta[@itemprop="availability"]/@content').extract_first()
        price = response.xpath('//span[@itemprop="price"]/text()').extract_first()
        category = response.xpath('//td[@class="vCSS_breadcrumb_td"]//a/text()').extract()[1:]
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract_first()
        options = False
        for match in re.finditer(r'TCN_addContent\("(.*)"\);', response.body):
            options = True
            loader = ProductLoader(item=Product(), response=response)
            parts = match.group(1).split('+#+')
            sub_name = parts[0]
            sub_id = parts[1]
            loader.add_value('name', name + ' ' + sub_name)
            loader.add_value('identifier', identifier + '_' + sub_id)
            loader.add_value('sku', identifier)
            loader.add_value('category', category)
            loader.add_value('url', response.url)
            loader.add_value('image_url', response.urljoin(image_url))
            loader.add_value('price', price)
            if loader.get_output_value('price') < 50:
                loader.add_value('shipping_cost', '8.50')
            if stock != 'InStock':
                loader.add_value('stock', 0)
            option_item = loader.load_item()
            metadata = KitBagMeta()
            metadata['size'] = sub_name
            player_found = False
            for team, players in self.teams.iteritems():
                for player_id, player in players.iteritems():
                    product_name = option_item['name'].upper()
                    player_name = player['name'].decode('utf')
                    if player_name.upper() in product_name or product_name.split()[0] == player_name.upper():
                        metadata['player'] = player_name
                        metadata['number'] = player['number']
                        player_found = True
                        break
                if player_found:
                    break
            option_item['metadata'] = metadata
            yield option_item
        if not options:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('identifier', identifier)
            loader.add_value('sku', identifier)
            loader.add_value('category', category)
            loader.add_value('url', response.url)
            loader.add_value('image_url', response.urljoin(image_url))
            loader.add_value('price', price)
            if loader.get_output_value('price') < 50:
                loader.add_value('shipping_cost', '8.50')
            if stock != 'InStock':
                loader.add_value('stock', 0)
            option_item = loader.load_item()
            metadata = False
            for team, players in self.teams.iteritems():
                for player_id, player in players.iteritems():
                    product_name = option_item['name'].upper()
                    player_name = player['name'].decode('utf')
                    if player_name.upper() in product_name or product_name.split()[0] == player_name.upper():
                        metadata = KitBagMeta()
                        metadata['player'] = player_name
                        metadata['number'] = player['number']
                        option_item['metadata'] = metadata
                        break
                if metadata:
                    break
            yield option_item


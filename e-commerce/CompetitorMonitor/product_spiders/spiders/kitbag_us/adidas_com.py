"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4976

The spider crawls Soccer apparel category
Collects all options.
"""
import scrapy
import csv
import os
import json
from copy import deepcopy
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from kitbagitems import KitBagMeta
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))

class AdidasSpider(scrapy.Spider):
    name = 'kitbag-adidas.com'
    allowed_domains = ['adidas.com']
    start_urls = ('http://origin-www.adidas.com/us/soccer-apparel?sz=120&start=0',)
    #  start_urls = ('http://www.adidas.com/us/soccer-apparel?sz=120&start=0',)
    teams = {}
    
    custom_settings = {'COOKIES_ENABLED': False}
    rotate_agent = True

    def __init__(self, *args, **kwargs):
        super(AdidasSpider, self).__init__(*args, **kwargs)

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
        products = response.xpath('//div[contains(@class, "product-info-wrapper")]//a[contains(@class, "product-link")]/@href').extract()
        for url in products:
            yield scrapy.Request(response.urljoin(url.replace('origin-', '')), callback=self.parse_product)

        pages = response.xpath(
                '//*[@id="top-pagination"]//a[@class="paging-arrow pagging-next-page"]/@href').extract()
        for url in pages:
            url = url.replace('http://www.adidas', 'http://origin-www.adidas')
            yield scrapy.Request(response.urljoin(url), callback=self.parse)

    def parse_product(self, response):
        sku = response.xpath('//input[@name="masterPid"]/@value').extract_first()
        name = response.xpath('//h1[@itemprop="name"]/text()').extract_first()
        name_color = response.xpath('//span[@class="product-color-clear"]/text()').extract_first()
        name += ' ' + name_color
        price = response.xpath('//span[@itemprop="price"]/text()').extract_first()
        category = response.xpath('//*[@id="product-breadcrumb"]//a/text()').extract()[2:]
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract_first()
        options = response.xpath('//select[@class="size-select"]//option')
        pz = response.xpath('//*[@id="personalization-block"]')
        for option in options:
            identifier = option.xpath('./@value').extract_first()
            if identifier == 'empty':
                continue
            loader = ProductLoader(item=Product(), response=response)
            option_name = option.xpath('./text()').extract_first().strip()
            loader.add_value('name', name + ' ' + option_name)
            loader.add_value('identifier', identifier)
            loader.add_value('sku', sku)
            loader.add_value('category', category)
            loader.add_value('url', response.url.replace('http://origin-', 'http://'))
            #  loader.add_value('url', response.url)
            loader.add_value('image_url', response.urljoin(image_url))
            loader.add_value('price', price)
            loader.add_value('brand', 'Adidas')
            option_item = loader.load_item()
            metadata = KitBagMeta()
            metadata['size'] = option_name
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
            if pz:
                yield scrapy.Request('http://cfg.adidas.com/configurator/services/miadidas-configurator/ppdo/article/{}/region/us/channel/1/partner/null'.format(sku),
                                     callback=self.parse_pz,
                                     meta={'product': option_item},
                                     dont_filter=True)
            else:
                yield option_item

    @staticmethod
    def parse_pz(response):
        product = response.meta['product']
        pz = json.loads(response.body.decode('utf-8', 'ignore'))
        # players
        for player_id, player in pz['parts']['pName-pNumber']['attributes']['textName-textNumber']['values'].iteritems():
            player_name = player['displayValue']
            player_price = extract_price(player['price'])
            if pz['parts']['sleeve_badge']:
                # badges
                for badge_id, badge in pz['parts']['sleeve_badge']['attributes']['league']['values'].iteritems():
                    badge_name = badge['displayValue']
                    badge_price = extract_price(badge['price'])
                    p = deepcopy(product)
                    p['name'] += ' {} {}'.format(player_name, badge_name)
                    p['price'] += player_price + badge_price
                    p['identifier'] += '_{}_{}'.format(player_id, badge_id)
                    yield p
            else:
                # only players, no badges
                p = deepcopy(product)
                p['name'] += ' {}'.format(player_name)
                p['price'] += player_price
                p['identifier'] += '_{}'.format(player_id)
                yield p



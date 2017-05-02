"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4974

The spider crawls Soccer category
Collects all options.
"""
import scrapy
import csv
import os
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from kitbagitems import KitBagMeta

HERE = os.path.abspath(os.path.dirname(__file__))

class FanaticsSpider(scrapy.Spider):
    name = 'kitbag-fanatics.com'
    allowed_domains = ['fanatics.com']
    start_urls = ('http://www.fanatics.com/Soccer',)
    teams = {}
    free_shipping_thres = None

    def __init__(self, *args, **kwargs):
        super(FanaticsSpider, self).__init__(*args, **kwargs)

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
        free_shipping_thres = response.xpath('//script[contains(text(),"FreeShipBannerThreshold")]/text()')\
                                           .re('FreeShipBannerThreshold:(\d+?),')
        if free_shipping_thres:
            self.free_shipping_thres = extract_price(free_shipping_thres[0])
        self.log('Free Shipping Thres: {}'.format(self.free_shipping_thres))
        for url in response.xpath('//*[@id="ContentInnerContainer"]//a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_products)

    def parse_products(self, response):
        for url in response.xpath('//div[@itemprop="itemListElement"]/div[1]/a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product)

        for url in response.xpath('//div[@class="row topPager navigation-frame"]//a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_products)

        for url in response.xpath('//a[text()="View All Products"]/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_products)

    def parse_product(self, response):
        identifier = response.xpath('//*[@id="data-product-id"]/@value').extract_first()
        name = response.xpath('//h1[@itemprop="name"]/text()').extract_first()
        category = response.xpath('//*[@id="browseHeaderContainer"]//a/text()').extract()[1:]
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract_first()
        brand = response.xpath('//meta[@itemprop="brand"]/@content').extract_first()
        products = response.xpath('//a[@class="sizeOption In sizeOptionElement "]')
        for product in products:
            loader = ProductLoader(item=Product(), response=response)
            sub_id = product.xpath('./@data-sku-id').extract_first()
            sub_name = product.xpath('./span[@class="size"]/text()').extract_first()
            price = product.xpath('./@data-price').extract_first()
            # stock = product.xpath('./@data-inventory-tier').extract_first()
            loader.add_value('name', name + ' ' + sub_name)
            loader.add_value('identifier', identifier + '_' + sub_id)
            loader.add_value('sku', identifier)
            loader.add_value('category', category)
            if brand:
                loader.add_value('brand', brand.title())
            loader.add_value('url', response.url)
            loader.add_value('image_url', response.urljoin(image_url))
            loader.add_value('price', price)
            loader.add_value('shipping_cost', '4.99')
            option_item = loader.load_item()
            if self.free_shipping_thres is not None and option_item['price'] and option_item['price'] >= self.free_shipping_thres:
                option_item['shipping_cost'] = '0.00'
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
        if not products:
            loader = ProductLoader(item=Product(), response=response)
            price = response.xpath('//meta[@itemprop="price"]/@content').extract_first()
            loader.add_value('name', name)
            loader.add_value('identifier', identifier)
            loader.add_value('sku', identifier)
            loader.add_value('category', category)
            if brand:
                loader.add_value('brand', brand.title())
            loader.add_value('url', response.url)
            loader.add_value('image_url', response.urljoin(image_url))
            loader.add_value('price', price)
            loader.add_value('shipping_cost', '4.99')
            option_item = loader.load_item()
            if self.free_shipping_thres is not None and option_item['price'] and option_item['price'] >= self.free_shipping_thres:
                option_item['shipping_cost'] = '0.00'
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

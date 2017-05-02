"""
Kitbag account
Real Madrid Store spider
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4926
"""
import re
import json
from decimal import Decimal

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request, FormRequest

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

class RealMadridStore(CrawlSpider):
    name = 'kitbag-realmadridstore'
    allowed_domains = ['shop.realmadrid.com']
    start_urls = ['http://shop.realmadrid.com/stores/realmadrid/en/c/football-kits/shop-by-players?cur=GBP',
                  'http://shop.realmadrid.com/stores/realmadrid/en/c/official-kit-15-16?cur=GBP',
                  'http://shop.realmadrid.com/stores/realmadrid/en/c/training?cur=GBP',
                  'http://shop.realmadrid.com/stores/realmadrid/en/c/apparel?cur=GBP']

    categories = LinkExtractor(restrict_css='.facetCategory, .nav-menu-kit')
    products = LinkExtractor(restrict_css='.productListLink')

    rules = (
        Rule(categories, callback='parse_list', follow=True),
        Rule(products, callback='parse_product')
        )

    def parse_list(self, response):
        formdata = {'__EVENTARGUMENT': '',
                    '__EVENTTARGET': 'ctl00$ContentMain$product_browse1$lv_pagingTop$lb_viewAll'}
        if response.css('.pages a'):
            yield FormRequest.from_response(response, formdata=formdata)

    def parse_product(self, response):
        if 'aspxerrorpath' in response.url:
            yield Request(response.request.meta['redirect_urls'][0], self.parse_product, dont_filter=True)
        base_product = True
        add_custom_personalization = False
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('url', '//link[@rel="canonical"]/@href')
        loader.add_value('category', 'Kits')
        heros_data = response.xpath('//script/text()').re('product\d{7} =(.+?});var')
        base_product_data = response.xpath('//script/text()').re('product\w{6} =(.+?});var')
        if not base_product_data:
            for p in self.parse(response):
                yield p
            return
        if not heros_data:
            data = json.loads(base_product_data[0])
        elif len(heros_data) == 1:
            data = json.loads(heros_data[0])
            base_product = False
        else:
            data = [json.loads(x) for x in heros_data]
            data = {x['ProductID']: x for x in data}
            heros = response.css('select.heroShirts')
            hero = heros.xpath('option[@selected]')
            if not hero:
                data = json.loads(base_product_data[0])
            else:
                data = data[int(hero.xpath('@value').extract_first())]
                base_product = False
                
        base_product_data = json.loads(base_product_data[0])
        gbp_url = response.xpath('//a[contains(@href, "?cur=GBP")]/@href').extract_first()
        if gbp_url:
            yield Request(response.urljoin(gbp_url), self.parse_product, dont_filter=True)
            return
        
        #Checking custom personalization
        printings = {p['PrintingTypeID']: p for p in base_product_data['printingitems']}
        custom_printings = printings.get(1)
        if custom_printings and base_product:
            add_custom_personalization = True
            
        loader.add_value('name', data['Description'])
        loader.add_xpath('sku', '//script/text()', re='sku":"(.+?)"')
        if data['Brand']:
            loader.add_value('brand', data['Brand']['Name'])
        loader.add_value('image_url', response.urljoin(data['ImageURL']))
        product = loader.load_item()
        player_from_name = re.search('with *([\w.\- ]+?) *(\d*|TBC) *printing', data['Description'], re.UNICODE)
        if player_from_name:
            player_name, number = player_from_name.groups()
        #sizes
        for variation in data['Variations']:
            size = variation['Description']
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value(None, product)
            loader.replace_value('identifier', variation['VariationId'])
            loader.add_value('name', size)
            loader.replace_value('price', variation['PriceActual'])
            if variation['PriceActual'] < 75:
                loader.replace_value('shipping_cost', '5.95')
            loader.replace_value('stock', int(variation['IsInStock']))
            item = loader.load_item()
            if player_from_name:
                item['metadata'] = {'player': player_name, 'number': number, 'size': size}
            else:
                item['metadata'] = {'size': size}
            yield item

            #Custom printings
            custom_item = None
            if add_custom_personalization:
                team_player_name = 'WILLIAMS'
                team_player_number = '10'
                team_player_id = 'WILLIAMS'
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value(None, item)
                loader.add_value('name', team_player_name)
                loader.add_value('name', team_player_number)
                price = Decimal(item['price']) + Decimal(str(custom_printings['PriceActual']))
                loader.replace_value('price', price)
                if price >= 75:
                    loader.replace_value('shipping_cost', 0)
                identifier = '-'.join((item['identifier'],
                                        str(custom_printings['PrintingID']),
                                        team_player_id))
                loader.replace_value('identifier', identifier)
                custom_item = loader.load_item()
                custom_item['metadata'] = {'player': team_player_name,
                                            'number': team_player_number,
                                            'size': size}
                yield custom_item
            
            #Badges
            printing = printings.get(3)
            if not printing:
                continue
            items = (item, custom_item) if custom_item else (item,)
            for base_item in items:
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value(None, base_item)
                loader.add_value('name', printing['PrintingDescription'])
                price = Decimal(item['price']) + Decimal(str(printing['PriceActual']))
                loader.replace_value('price', price)
                if price >= 75:
                    loader.replace_value('shipping_cost', 0)
                identifier = item['identifier'] + '-' + str(printing['PrintingID'])
                loader.replace_value('identifier', identifier)
                badge_item = loader.load_item()
                badge_item['metadata'] = item['metadata'].copy()
                yield badge_item
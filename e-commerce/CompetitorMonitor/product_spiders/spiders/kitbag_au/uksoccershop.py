# -*- coding: utf-8 -*-
import os
import re
import csv
import json

from copy import deepcopy
from scrapy.spider import BaseSpider
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc, url_query_parameter, add_or_replace_parameter

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price_eu, extract_price

from kitbagitems import KitBagMeta

HERE = os.path.abspath(os.path.dirname(__file__))

class UkSoccerShopSpider(BaseSpider):
    name = u'kitbag_au-uksoccershop.com'
    allowed_domains = ['www.uksoccershop.com']
    start_urls = ['http://www.uksoccershop.com']

    teams = {}

    formdata = {'currency': 'AUD',
                'delivery_destination': '13',
                'update_currency_destination': 'Update'}
    
    shipping_cost = None
    items = []
    added_to_basket = False

    def __init__(self, *args, **kwargs):
        super(UkSoccerShopSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.idled, signals.spider_idle)

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
        formdata = {'currency': 'AUD',
                    'delivery_destination': '13',
                    'update_currency_destination': 'Update'}
        yield FormRequest("http://www.uksoccershop.com", formdata=self.formdata, method='POST')
    
    def proxy_service_check_response(self, response):
        return 'You are not Authorized to access this page' in response.body
    
    def parse(self, response):
        formdata = {'currency': 'AUD',
                    'delivery_destination': '13',
                    'update_currency_destination': 'Update'}

        base_url = "http://www.uksoccershop.com"

        categories = response.xpath('//li[contains(a/span/text(), "Football Shirts")]//a/@href').extract()
        categories += response.xpath('//div[h4/span/a/text()="Euro 2016 National Teams"]//div[contains(@class, "newitem")]/a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))

        products = response.xpath('//div[contains(@class, "productList")]//div[@class="productListLink"]/a/@href').extract()
        for product in products:
            yield FormRequest(urljoin_rfc(base_url, product), formdata=self.formdata, method='POST', callback=self.parse_product)

        if products:
            next_url = "http://www.uksoccershop.com/index.html?cPath=%s&page=%s&ppp=48"
            cat_id = re.findall('current_category_id = (\d+)', response.body)
            if not cat_id:
                cat_id = response.xpath('//input[@name="cPath"]/@value').extract()
                cat_id = cat_id[0].split('_') if cat_id else None
            if cat_id:
                cat_id = cat_id[-1]
                current_page = url_query_parameter(response.url, 'page', '1')
                next_page = int(current_page) + 1
                yield Request(next_url % (cat_id, next_page))
            else:
                request_to_urls = re.findall("var request_to = '(.*)'\+ 48", response.body)
                all_products = filter(lambda x: x if 'main_page' in x else None,request_to_urls)
                if all_products:
                    yield Request(response.urljoin(all_products[0])+'9999')

    def parse_product(self, response):
        if self.proxy_service_check_response(response):
            yield response.request.replace(dont_filter=True, meta={'dont_merge_cookies': True})
            return
        if not response.xpath('//option[@selected][contains(., "Australia")]'):
            yield FormRequest(response.url, formdata=self.formdata)
            return
        more_options = response.xpath('//ul[@class="swatchesdisplay"]//a/@href').extract()
        for option in more_options:
            yield FormRequest(option, formdata=self.formdata, method='POST', callback=self.parse_product)

        loader = ProductLoader(item=Product(), response=response)
        name = response.xpath('//h1[@itemprop="name"]/text()').extract()[0].strip()
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])
        price = response.xpath('//div[@id="pro_heading"]//span[@itemprop="price"]/text()').extract()
        if not price	:
            price = response.xpath('//span[@class="prodPRICE onChangePrice"]/text()').extract()
        if not price:
            price = response.xpath('//span[@itemprop="price"]/span[@class="productSalePrice"]/text()').extract()

        loader.add_value('price', extract_price_eu(price[0]))
        categories = response.xpath('//div[@id="nav_submenu_contain"]/div/a/text()').extract()[1:-1]
        loader.add_value('category', categories)

        sku = response.xpath('//input[@name="productid"]/@value').extract()
        if not sku:
            sku = response.xpath('//input[@name="products_id"]/@value').extract()
        sku = sku[0]
        loader.add_value('identifier', sku)
        loader.add_value('sku', sku)
        brand = response.xpath('//tr[contains(.//text(), "Manufactured by")]//span[@class="prod_desc_col"]/text()').extract()
        brand = brand[0].split(',')[0] if brand else ''
        loader.add_value('brand', brand)
        loader.add_value('shipping_cost', 10.64)

        item = loader.load_item()
        player_name = ''
        player_number = ''
        player_data = re.search('\((.*)-(.*)\)', response.url)
        if player_data and '(white-black)' not in response.url.lower():
            player_name, player_number = player_data.groups()

        addition_price_shirt = response.xpath('//div[@class="pdp-personalization"]/h2/text()').re('\d+\,\d+')


        options = response.xpath('//select[contains(@onchange, "checkSizeQuantity")]/option')
        tables_options = response.xpath('//table[@summary="Product Options"]')
        if options:
            stock_url = 'http://www.uksoccershop.com/index.php?main_page=checkSizeQuantity'
            for option in options:
                option_item = deepcopy(item)
                name = option.xpath('text()').extract()[0]
                option_id = option.xpath('@value').extract()[0]

                formdata = {'product_id': sku, 'type':'new', 'value': option_id}

                option_item['identifier'] += '-' + option_id
                option_item['name'] += ' ' + name
                if addition_price_shirt:
                    add_price = extract_price_eu(addition_price_shirt[0])
                    team_found = False
                    for team, players in self.teams.iteritems():
                        product_name = option_item['name'].upper()
                        if team.upper() in product_name or product_name.split()[0] == team.upper():
                            team_found = True
                            items = []
                            for player_id, player in players.iteritems():
                                player_item = deepcopy(option_item)
                                player_item['identifier'] += '-' + player_id
                                player_item['name'] += u' ' + player['name'].decode('utf') + ' ' + player['number']
                                player_item['price'] += add_price
        
                                metadata = KitBagMeta()
                                metadata['size'] = option.xpath('text()').extract()[0]
                                metadata['player'] = player['name'].decode('utf')
                                metadata['number'] = player['number']
                                player_item['metadata'] = metadata
                                items.append(player_item)
                            req = FormRequest(stock_url, formdata=formdata, callback=self.parse_stock, meta={'items': items})
                            yield req
                    if not team_found:
                        metadata = KitBagMeta()
                        metadata['size'] = option.xpath('text()').extract()[0]
                        metadata['player'] = player_name
                        metadata['number'] = player_number
                        option_item['metadata'] = metadata
                        req = FormRequest(stock_url, formdata=formdata, callback=self.parse_stock, meta={'items': [option_item]})
                        yield req
                else:
                    metadata = KitBagMeta()
                    metadata['size'] = option.xpath('text()').extract()[0]
                    metadata['player'] = player_name
                    metadata['number'] = player_number
                    option_item['metadata'] = metadata
                    req = FormRequest(stock_url, formdata=formdata, callback=self.parse_stock, meta={'items':[option_item]})
                    yield req

        if tables_options:
            for table_options in tables_options:
                options = table_options.xpath('.//tr[td[@class="product_quantity_options_qty"]]')
                for option in options:
                    option_variations = options.xpath('.//td[@class="product_quantity_options_qty"]')
                    for i, option_variation in enumerate(option_variations):
                        option_item = deepcopy(item)
                        desc = option.xpath('.//td[@class="product_quantity_options_text"]/text()').extract()[0]
                        size = table_options.xpath('.//tr[@class="product_quantity_grid_header"]/td/div/text()').extract()[i+1]
                        desc += ' ' + size
                        option_item['name'] += ' ' + desc
                        option_item['price'] = extract_price(option_variation.xpath('.//input[@name="quantity_hidden"]/@value').extract()[0])
                        option_id = option_variation.xpath('preceding-sibling::input[contains(@id, "attrib-")]/@value').extract()[-1]
                        option_item['identifier'] += '-' + option_id
                        option_item['sku'] = option_item['identifier']

                        metadata = KitBagMeta()
                        metadata['size'] = size
                        metadata['player'] = player_name
                        metadata['number'] = player_number
                        option_item['metadata'] = metadata
                        if self.shipping_cost:
                            option_item['shipping_cost'] = self.shipping_cost
                            yield option_item
                        else:
                            self.items.append(option_item)

        if not options and not tables_options:
            stock = response.xpath('//span[@class="stock_available" and contains(text(), "Available Now")]')
            if not stock:
                item['stock'] = 0
            elif not self.added_to_basket:
                formdata = {
                    'products_id': sku,
                    'cart_quantity': '1'}
                url = add_or_replace_parameter(response.url, 'action', 'add_product')
                url = add_or_replace_parameter(url, 'number_of_uploads', 0)
                yield FormRequest(url,
                                  self.run_basket_parse,
                                  formdata=formdata)
                self.added_to_basket = True
                
            if self.shipping_cost:
                item['shipping_cost'] = self.shipping_cost
                yield item
            else:
                self.items.append(item)

    def parse_stock(self, response):
        items = response.meta['items']

        stock_data = json.loads(response.body)

        for item in items:
            if 'outofstock' in stock_data['new_data']:
                item['stock'] = 0
            elif not self.added_to_basket:
                formdata = {
                    'products_id': item['sku'],
                    'cart_quantity': '1'}
                url = add_or_replace_parameter(item['url'], 'action', 'add_product')
                url = add_or_replace_parameter(url, 'number_of_uploads', 0)
                yield FormRequest(url,
                                  self.run_basket_parse,
                                  formdata=formdata)
                self.added_to_basket = True
                
            if self.shipping_cost:
                item['shipping_cost'] = self.shipping_cost
                yield item
            else:
                self.items.append(item)
    
    def run_basket_parse(self, response):
        formdata = {'action': 'deliveryInfo', 'country_id': '13'}
        yield FormRequest(
            'http://www.uksoccershop.com/index.php?main_page=ajax_calculator_new',
            self.parse_shipping,
            formdata=formdata)
        
    def parse_shipping(self, response):
        self.shipping_cost = extract_price_eu(response.css('.value::text').extract_first())
        
    def idled(self, spider):
        if spider != self or not self.items:
            return
        self.crawler.engine.crawl(Request(self.start_urls[0], 
                                          self.process_items, 
                                          dont_filter=True), 
        self)

    def process_items(self, response):
        for item in self.items:
            item['shipping_cost'] = self.shipping_cost
            yield item
        self.items = None
    
        
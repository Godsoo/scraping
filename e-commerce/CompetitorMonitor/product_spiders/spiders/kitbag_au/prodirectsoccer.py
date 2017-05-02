# -*- coding: utf-8 -*-

"""
Account: Kitbag AU
Name: kitbag-prodirectsoccer.com
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5067
The spider has been copied from the Kitbag UK account
"""
import os
import csv
import re
import paramiko
from decimal import Decimal
from scrapy import Spider, Request, FormRequest
from scrapy.utils.url import add_or_replace_parameter
from product_spiders.items import Product, ProductLoader
from product_spiders.lib.schema import SpiderSchema
from product_spiders.utils import extract_price
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


class ProDirectSoccerSpider(Spider):
    name = u'kitbag_au-prodirectsoccer.com'
    allowed_domains = ['prodirectsoccer.com']
    start_urls = ['http://www.prodirectsoccer.com/replica.aspx']

    exchange_rate = None
    added_to_basket = False
    shipping_cost = None
    items = []

    def __init__(self, *args, **kwargs):
        super(ProDirectSoccerSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.idled, signals.spider_idle)

    def start_requests(self):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = 'gtX34aJy'
        username = 'kitbag'
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        file_path = os.path.join(HERE, 'ExchangeRates.csv')
        sftp.get('Exchange Rates/Exchange Rates.csv', file_path)

        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Currency'] == 'GBP-AUD':
                    self.exchange_rate = extract_price(row['Rate'])
                    break

        self.logger.info('Exchange rate is %s' % str(self.exchange_rate))
        for url in self.start_urls:
            yield Request(url, callback=self.parse)  
            
    def parse(self, response):
        links = response.xpath('//ul[@id="primary-nav"]/li[contains(a/text(), '
                               '"Replica")]//a/@href').extract()
        for url in links:
            url = response.urljoin(url)
            url = add_or_replace_parameter(url, 'cur', 'GBP')
            url = add_or_replace_parameter(url, 'p', '1')
            url = add_or_replace_parameter(url, 'pp', '96')
            url = add_or_replace_parameter(url, 'o', 'lth')
            yield Request(url, callback=self.parse_list)

    def parse_list(self, response):
        next_page = response.xpath('//li[@class="next-page"]/a/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]), callback=self.parse_list)

        products = response.xpath('//div[@class="list"]/div[@class="item"]')
        for product in products:
            url = product.xpath('./a/@href').extract()
            if url:
                req = Request(response.urljoin(url[0]), callback=self.parse_product)
                brand = product.xpath('./span[contains(@class, "small-brand-logo")]/text()').extract()
                if brand:
                    req.meta['brand'] = brand[0].strip()
                yield req

    def parse_product(self, response):
        schema = SpiderSchema(response)
        pdata = schema.get_product()

        sku = pdata.get('mpn', '')
        image = pdata['image'].replace('example.com', 'prodirectsoccer.com')
        main_id = response.xpath('//div[@id="define-profile"]/@data-quickref').extract()[0]
        main_name = pdata['name']
        main_price = extract_price(pdata['offers']['properties']['price']) * self.exchange_rate
        main_brand = response.meta.get('brand')

        sizes = response.xpath('//select[@id="size"]/option[@value!=""]')
        player_sel_label = response.xpath('//label[@for="pers-opt1"]/text()').extract()
        player_tourn_sel_label = response.xpath('//label[@for="pers-opt2"]/text()').extract()

        for size_opt in sizes:
            size_desc = size_opt.xpath('text()').extract()[0].strip()
            size_value = size_opt.xpath('@value').extract()[0].strip()
            in_stock = True
            if ' ' in size_desc:
                size_desc, stock = size_desc.split(' ', 1)
                if 'OUT OF STOCK' in stock.upper():
                    in_stock = False
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', main_id + 'x' + size_value)
            loader.add_value('name', main_name + ' - ' + size_desc)
            loader.add_value('sku', sku)
            loader.add_value('price', main_price)
            loader.add_value('url', response.url)
            loader.add_value('image_url', image)
            if main_brand:
                loader.add_value('brand', main_brand)
            loader.add_value('category', 'Replicas')
            if not in_stock:
                loader.add_value('stock', 0)
            item = loader.load_item()
            item['metadata'] = {'size': size_desc}
            
            if not self.added_to_basket and in_stock:
                formdata = {
                    'sizeregion': 'UK',
                    'size': size_value, 
                    'quantity': '1', 
                    'buynow': '1',
                    'pers-type': '0'}
                yield FormRequest(response.url, 
                                  self.run_basket_parse, 
                                  formdata=formdata)
                self.added_to_basket = True
                
            if self.shipping_cost:
                item['shipping_cost'] = self.shipping_cost
                yield item
            else:
                self.items.append(item)

            if player_sel_label:
                player_sel_price = extract_price(player_sel_label[0]) * self.exchange_rate
                players = response.xpath('//select[@id="pers-player"]/option[@value!=""]')
                for player_opt in players:
                    player_desc = player_opt.xpath('text()').extract()[0].strip()
                    player_value = player_opt.xpath('@value').extract()[0].strip()
                    new_item = Product(item)
                    new_item['identifier'] += 'x' + player_value
                    new_item['name'] += ' - ' + player_desc
                    new_item['price'] = Decimal(new_item['price']) + player_sel_price
                    try:
                        player_number, player_name = re.search(r'(\d+)\s(.*)', player_desc).groups()
                        new_item['metadata']['player'] = player_name.strip()
                        new_item['metadata']['number'] = player_number
                    except:
                        pass
                    if new_item.get('shipping_cost'):
                        yield new_item
                    else:
                        self.items.append(new_item)

                    if player_tourn_sel_label:
                        player_tourn_price = extract_price(player_tourn_sel_label[0]) * self.exchange_rate
                        tournaments = response.xpath('//select[@id="pers-tournament"]/option[@value!=""]')
                        for tourn_opt in tournaments:
                            tourn_desc = tourn_opt.xpath('text()').extract()[0].strip()
                            tourn_value = tourn_opt.xpath('@value').extract()[0].strip()
                            new_item = Product(item)
                            new_item['identifier'] += 'x' + player_value + 'x' + tourn_value
                            new_item['name'] += ' - ' + player_desc + ' - ' + tourn_desc
                            new_item['price'] = Decimal(new_item['price']) + player_tourn_price
                            try:
                                player_number, player_name = re.search(r'(\d+)\s(.*)', player_desc).groups()
                                new_item['metadata']['player'] = player_name.strip()
                                new_item['metadata']['number'] = player_number
                            except:
                                pass
                            if new_item.get('shipping_cost'):
                                yield new_item
                            else:
                                self.items.append(new_item)
    
    def run_basket_parse(self, response):
        formdata = {
            'dlw100$Update$1': '1', 
            'ddlDeliveryCC': '36', 
            'dlw$MatrixID': '1', 
            '__EVENTTARGET': 'dlw100$DeliveryUpdate'}
        yield FormRequest('http://www.prodirectsoccer.com/V3_1/V3_1_Basket.aspx',
                          self.parse_shipping,
                          formdata=formdata)
        
    def parse_shipping(self, response):
        tmp = response.xpath('//div[text()="Delivery:"]/following-sibling::div/strong/text()').extract_first()
        self.shipping_cost = extract_price(tmp) * self.exchange_rate
    
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
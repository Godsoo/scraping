# -*- coding: utf-8 -*-

"""
Account: Kitbag
Name: kitbag_us-prodirectsoccer.com
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5002
"""

import re
from decimal import Decimal
from scrapy import Spider, Request
from scrapy.utils.url import add_or_replace_parameter
from product_spiders.items import Product, ProductLoader
from product_spiders.lib.schema import SpiderSchema
from product_spiders.utils import extract_price


class ProDirectSoccerSpider(Spider):
    name = u'kitbag_us-prodirectsoccer.com'
    allowed_domains = ['prodirectsoccer.com']
    start_urls = [
        'http://www.prodirectsoccer.com/us/fanshop.aspx?cur=USD'
    ]

    def parse(self, response):
        links = response.xpath('//a/@href[contains(., "replica")]').extract()
        for url in links:
            url = response.urljoin(url.strip())
            url = add_or_replace_parameter(url, 'cur', 'USD')
            url = add_or_replace_parameter(url, 'p', '1')
            url = add_or_replace_parameter(url, 'pp', '96')
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
        main_price = extract_price(pdata['offers']['properties']['price'])
        main_brand = response.meta.get('brand')
        shipping = '9.93'

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
            loader.add_value('shipping_cost', shipping)
            loader.add_value('url', response.url)
            loader.add_value('image_url', image)
            if main_brand:
                loader.add_value('brand', main_brand)
            loader.add_value('category', 'Replicas')
            if not in_stock:
                loader.add_value('stock', 0)
            item = loader.load_item()
            item['metadata'] = {'size': size_desc}
            yield item

            if player_sel_label:
                player_sel_price = extract_price(player_sel_label[0])
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
                    yield new_item

                    if player_tourn_sel_label:
                        player_tourn_price = extract_price(player_tourn_sel_label[0])
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
                            yield new_item
 

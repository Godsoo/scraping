# -*- coding: utf-8 -*-
import os
import csv
import json
from copy import deepcopy
from time import time

import paramiko
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT
from urlparse import urljoin as urljoin_rfc

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class KitBagSpider(BaseSpider):
    name = u'kitbag_us-kitbag.com'
    allowed_domains = ['kitbag.com']

    filename = os.path.join(HERE, 'kitbag_us_products.csv')
    #start_urls = ('file://' + filename,)
    start_urls = ['http://www.kitbag.com/stores/kitbag/en/product/england-fa-crest-lion-flags/151002']
    shipping_cost = None
    free_delivery_over = None

    cookies = {'KB_44_PriceZoneID': 643, 
               'Kitbag_T36_NoFreeDelivery': False, 
               'KB_44_Currency': 'USD', 
               'KB_44_CurrencyId': 3,
               'KB_44_LocationID': 206,
               'KB_44_LocationISO2': 'US',
               'KB_44_Language': 1,
               'KB_44_network': 'KITBAG',
               'KB_44_BasketID': int(time()*1.305)}

    def parse(self, response):
        formdata = {}
        formdata['__VIEWSTATEGENERATOR'] = response.xpath('//input[@name="__VIEWSTATEGENERATOR"]/@value').extract()[0]
        formdata['__EVENTVALIDATION'] = response.xpath('//input[@name="__EVENTVALIDATION"]/@value').extract()[0]
        formdata['__VIEWSTATE'] = response.xpath('//input[@name="__VIEWSTATE"]/@value').extract()[0]
        formdata['__EVENTTARGET'] = ''
        formdata['ctl00$ScriptManager1'] = ''
        formdata['ctl00$ContentMain$product_details1$dd_quantity'] = '1'
        formdata['ctl00$ContentMain$product_details1$imgbtn_addToBasket.x'] = '0'
        formdata['ctl00$ContentMain$product_details1$imgbtn_addToBasket.y'] = '0'

        req = FormRequest.from_response(response, formname='aspnetForm',  formdata=formdata, callback=self.parse_shipping, cookies=self.cookies)
        yield req

    def parse_shipping(self, response):
        subtotal = response.xpath('//td[@class="bskTotalsPrice"]/span/text()').extract()
        if subtotal:
            subtotal = extract_price(subtotal[0])
            self.log('Subtotal {}'.format(subtotal))
        spend_more = response.xpath('//div[@id="ctl00_ContentMain_basket1_pnl_spendMore"]/span[@class="basketSM"]/text()').extract()
        if spend_more:
            spend_more = extract_price(spend_more[0])
            self.log('Spend a further {} to qualify for FREE Standard Delivery.'.format(spend_more))
        if subtotal and spend_more:
            self.free_delivery_over = subtotal + spend_more

        shipping_cost = response.xpath('//select[contains(@id, "shippingMethods")]/option/text()').re('(\d+\.\d+)')
        try:
            self.shipping_cost = extract_price(shipping_cost[0])
            self.logger.info('Shipping cost is %s' %self.shipping_cost)
        except IndexError:
            self.logger.error('No shipping cost parsed from basket. Spider will be closed')
            #return

        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = 'gtX34aJy'
        username = 'kitbag'
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.get('kitbag_us_products.csv', self.filename)

        with open(self.filename) as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield Request('http://www.kitbag.com/stores/kitbag/en/search/' + row['PID'],
                              dont_filter=True, callback=self.parse_products, meta={'row': row})

    def parse_products(self, response):
        products = response.xpath('//div[@class="productListItem"]/div[@class="productListLink"]/a/@href').extract()
        for url in products:
            yield Request(response.urljoin(url) + '?cur=USD', dont_filter=True, callback=self.parse_product, meta=response.meta)

        if not products:
            metadata = dict()
            row = response.meta['row']

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('url', '')
     
            name = row['Product Description'].decode('unicode_escape') + ' ' + row['Size Description']
            metadata['size'] = row['Size Description']
            if row['HERO NAME'] != 'N/A':
                name += ' ' + row['HERO NAME'].decode('unicode_escape') + ' ' + row['HERO NUMBER']
                metadata['player'] = row['HERO NAME']
                metadata['number'] = row['HERO NUMBER']            
            loader.add_value('name', name)
            loader.add_value('image_url', '')
            loader.add_value('category', '')
            loader.add_value('brand', row['Merret Department'])
            loader.add_value('price', 0)
            loader.add_value('identifier', row['SKU VID'].decode('unicode_escape'))
            loader.add_value('sku', row['SKU VID'].decode('unicode_escape'))
            loader.add_value('stock', 0)
            item = loader.load_item()

            item['metadata'] = metadata
            yield item

    def parse_product(self, response):
        row = response.meta['row']
        metadata = dict()

        loader = ProductLoader(item=Product(), response=response)
        name = response.xpath('//h1[@itemprop="name"]/text()').extract_first() or response.xpath(
            '//div[@id="pdTitle"]/h1/text()').extract_first() or response.xpath(
            '//div[@class="selectorProductTitle"]/span/text()').extract_first()
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('image_url', 'http://feo.kbobject.com/kb-' + row['PID'] + '.jpg')
        loader.add_value('category', '')
        loader.add_value('brand', row['Merret Department'])
        price = response.xpath('//span[@itemprop="price"]/text()').extract_first() or response.xpath(
            '//span[contains(@id, "PdProductPrice")]/text()').extract_first() or response.xpath(
            '//span[@class="selectorProductPrice"]/text()').extract_first()
        price = extract_price(price) if price else ''
        loader.add_value('price', price)
        loader.add_value('identifier', row['SKU VID'].decode('unicode_escape'))
        loader.add_value('sku', row['SKU VID'].decode('unicode_escape'))
        item = loader.load_item()

        options = []
        options_data = response.xpath('//script/text()').re('product\d{7} =(.+?});var')
        options_data += response.xpath('//script/text()').re('product\d{6} =(.+?});var')
        for option_data in options_data:
            option = json.loads(option_data)
            options.append(option)

        player_name = row['HERO NAME'].decode('unicode_escape')
        number = row['HERO NUMBER'].decode('unicode_escape')
        if player_name != 'N/A' and number != 'N/A':
            player = player_name + ' ' + number
            player_found = False
            metadata['player'] = player_name
            metadata['number'] = number
            for option in options:
                if player.upper() in option.get('Description', '').upper():
                    player_found = True
                    variations = option.get('Variations')
                    if variations:
                        item_found = None
                        for variation in variations:
                            if row['Size Description'].upper().strip() == variation['Description'].upper().strip():
                                option_item = deepcopy(item)
                                option_item['name'] = option.get('Description', '') + ' ' + variation['Description']
                                option_item['price'] = extract_price(str(variation['PriceActual']))
                                if not variation['IsInStock']:
                                    option_item['stock'] = 0
                                
                                metadata['size'] = variation['Description']
                                item_found = option_item
                                item_found['metadata'] = metadata
                                break

                        if item_found:
                            if item_found['price'] <= self.free_delivery_over:
                                item_found['shipping_cost'] = self.shipping_cost
                            yield item_found
                            return

            if not player_found:
                self.log('NOT PLAYER FOUND: %s' % response.url)
               
                item_found = None
                for option in options:
                    variations = option.get('Variations')
                    if variations:
                        for variation in variations:
                            if row['Size Description'].upper().strip() == variation['Description'].upper().strip():
                                print_item = option.get('printingitems', None)
                                if not print_item:
                                    continue
                                option_item = deepcopy(item)
                                option_item['name'] = option.get('Description', '') + ' ' + variation['Description'] +' ' + player_name + ' ' + number
                                option_item['price'] = extract_price(str(variation['PriceActual']))
                                option_item['price'] += extract_price(str(print_item[0]['PriceActual']))
                                self.log('PRINT OPTION FOUND: %s, %s, PLAYER: %s %s' % (str(print_item[0]['PriceActual']), response.url, player_name, number))
                                if not variation['IsInStock']:
                                    option_item['stock'] = 0

                                item_found = option_item
                                metadata['size'] = variation['Description']
                                item_found['metadata'] = metadata
                                break

                        if item_found:
                            if item_found['price'] <= self.free_delivery_over:
                                item_found['shipping_cost'] = self.shipping_cost
                            yield item_found
                            return
                        else:
                            self.log('NO PRINT OPTION FOR URL: %s, PLAYER: %s %s' % (response.url, player_name, number))
                if not item_found:
                    for option in options:
                        variations = option.get('Variations')
                        if variations:
                            for variation in variations:
                                if row['Size Description'].upper().strip() == variation['Description'].upper().strip():
                                    option_item = deepcopy(item)
                                    option_item['name'] = option.get('Description', '') + ' ' + variation['Description']
                                    option_item['price'] = extract_price(str(variation['PriceActual']))
                                    if not variation['IsInStock']:
                                        option_item['stock'] = 0
                                    item_found = option_item
                                    item_found['metadata'] = {'size': variation['Description']}
                                    break
                    
                            if item_found:
                                if item_found['price'] <= self.free_delivery_over:
                                    item_found['shipping_cost'] = self.shipping_cost
                                yield item_found
                                return
        else:    
            for option in options:
                variations = option.get('Variations')
                if variations:
                    item_found = None
                    for variation in variations:
                        if row['Size Description'].upper().strip() == variation['Description'].upper().strip():
                            option_item = deepcopy(item)
                            option_item['name'] = option.get('Description', '') + ' ' + variation['Description']
                            option_item['price'] = extract_price(str(variation['PriceActual']))
                            if not variation['IsInStock']:
                                option_item['stock'] = 0
                            item_found = option_item
                            item_found['metadata'] = {'size': variation['Description']}
                            break
                    
                    if item_found:
                        if item_found['price'] <= self.free_delivery_over:
                            item_found['shipping_cost'] = self.shipping_cost
                        yield item_found
                        return


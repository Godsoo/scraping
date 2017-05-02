# -*- coding: utf-8 -*-
import os
import csv
import json
import base64
from copy import deepcopy

import paramiko
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

from cStringIO import StringIO

from kitbagitems import KitBagMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class KitBagSpider(BaseSpider):
    name = u'kitbag_au-kitbag.com'
    allowed_domains = ['kitbag.com']

    filename = os.path.join(HERE, 'kitbag_au_products.csv')
    start_urls = ['http://www.kitbag.com/stores/kitbag/en/product/england-fa-crest-lion-flags/151002?cur=AUD']
    shipping_cost = None


    cookies = {}

    def start_requests(self):
       req = Request('http://www.kitbag.com/stores/kitbag/en/product/england-fa-crest-lion-flags/151002?cur=AUD', callback=self.set_cookies)
       req.meta['proxy'] = "http://52.62.200.83:3128"

       user_pass = base64.encodestring('griffin:wells1897')
       req.headers['Proxy-Authorization'] = 'Basic ' + user_pass
       yield req

    def set_cookies(self, response):
        cookies = []
        for k, v in response.headers.iteritems():
            if k == 'Set-Cookie':
                cookies = v
        self.cookies = cookies
        req = Request('http://www.kitbag.com/stores/kitbag/en/product/england-fa-crest-lion-flags/151002?cur=AUD', dont_filter=True)
        req.headers['Set-Cookie'] = self.cookies
        yield req
        

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

        req = FormRequest.from_response(response, formname='aspnetForm',  formdata=formdata, callback=self.parse_shipping)
        req.headers['Set-Cookie'] = self.cookies
        yield req

    def parse_shipping(self, response):
        req = Request("http://www.kitbag.com/stores/kitbag/en/basket/basket?atb=True", dont_filter=True, callback=self.parse_shipping1)
        req.headers['Set-Cookie'] = self.cookies
        yield req

    def parse_shipping1(self, response):
        shipping_cost = response.xpath('//select[contains(@id, "shippingMethods")]/option/text()').re('(\d+\.\d+)')
        self.shipping_cost = extract_price(shipping_cost[0])

        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = 'gtX34aJy'
        username = 'kitbag'
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.get('kitbag_au_products.csv', self.filename)

        with open(self.filename) as f:
            reader = csv.DictReader(f)
            for row in reader:
                req = Request('http://www.kitbag.com/stores/kitbag/en/search/' + row['PID'],
                              dont_filter=True, callback=self.parse_products, meta={'row': row})
                req.headers['Set-Cookie'] = self.cookies
                yield req

    def parse_products(self, response):
        products = response.xpath('//div[@class="productListItem"]/div[@class="productListLink"]/a/@href').extract()
        for url in products:
            req = Request(response.urljoin(url), dont_filter=True, callback=self.parse_product, meta=response.meta)
            req.headers['Set-Cookie'] = self.cookies
            yield req

        if not products:
            row = response.meta['row']

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('url', '')
     
            name = row['Product Description'] + ' ' + row['Size Description'] + ' ' + row['HERO NAME'] + ' ' + row['HERO NUMBER']
            loader.add_value('name', name)
            loader.add_value('image_url', '')
            loader.add_value('category', '')
            loader.add_value('brand', row['Merret Department'])
            loader.add_value('price', 0)
            loader.add_value('stock', 0)
            loader.add_value('identifier', row['SKU VID'].decode('unicode_escape'))
            loader.add_value('sku', row['SKU VID'].decode('unicode_escape'))
            item = loader.load_item()
            yield item

    def parse_product(self, response):

        row = response.meta['row']

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
        size = row['Size Description'].strip()

        metadata = KitBagMeta()
        metadata['size'] = size
        metadata['player'] = player_name
        metadata['number'] = number
        item['metadata'] = metadata

        if player_name != 'N/A' and number != 'N/A':
            player = player_name + ' ' + number
            player_found = False
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

                                item_found = option_item
                                break

                        if item_found:
                            if item_found['price'] <= 125:
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
                                break

                        if item_found:
                            if item_found['price'] <= 125:
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
                                    break
                    
                            if item_found:
                                if item_found['price'] <= 125:
                                    item_found['shipping_cost'] = self.shipping_cost
                                yield item_found
                                return
        else:    
            for option in options:
                if 'with ' in option.get('Description', ''):
                    continue
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
                            break
                    
                    if item_found:
                        if item_found['price'] <= 125:
                            item_found['shipping_cost'] = self.shipping_cost
                        yield item_found
                        return

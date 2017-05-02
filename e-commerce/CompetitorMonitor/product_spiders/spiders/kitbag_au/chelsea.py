"""
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5049
The spider has been copied from the Kitbag UK account
"""

import os
import csv
import json
from decimal import Decimal, ROUND_DOWN
import re
import paramiko

from scrapy.spider import BaseSpider
from scrapy.http import Request, FormRequest
from scrapy.utils.url import add_or_replace_parameter

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price

from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


def format_price(price, rounding=None):
    if price is None:
        return Decimal('0.00')

    return price.quantize(Decimal('0.01'), rounding=rounding or ROUND_DOWN)


class ChelseaMegaStore(BaseSpider):
    name = 'kitbag_au-chelseamegastore.com'
    allowed_domains = ['chelseamegastore.com']
    start_urls = ['http://www.chelseamegastore.com/stores/chelsea/en/c/football-kits?cur=GBP',
                  'http://www.chelseamegastore.com/stores/chelsea/en/c/training?cur=GBP',
                  'http://www.chelseamegastore.com/stores/chelsea/en/c/adidas?cur=GBP',
                  'http://www.chelseamegastore.com/stores/chelsea/en/c/fashion?cur=GBP',
                  'http://www.chelseamegastore.com/stores/chelsea/en/c/accessories?cur=GBP']
    extracted_identifiers = []
    free_delivery_over = None

    exchange_rate = None
    shipping_cost = None

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

        yield Request('http://www.chelseamegastore.com/stores/chelsea/en/product/chelsea-water-bottle---blue/176293?cur=AUD',
                      callback=self.parse_shipping)

    def parse_shipping(self, response):
        free_delivery_over = response.xpath('//ul[@class="uspContent"]/li/text()').re(u'Free UK Delivery On Orders Over \xa3(.*)')
        if not free_delivery_over:
            free_delivery_over = response.xpath('//ul[@class="uspContent"]/li/text()').re(u'Free Delivery On Orders Over \xa3(.*)')
        if free_delivery_over and self.exchange_rate:
            self.free_delivery_over = extract_price(free_delivery_over[0]) * self.exchange_rate
            self.log('Free delivery over {} GBP'.format(self.free_delivery_over))
        formdata = {}
        formdata['__VIEWSTATEGENERATOR'] = response.xpath('//input[@name="__VIEWSTATEGENERATOR"]/@value').extract()[
            0]
        formdata['__EVENTVALIDATION'] = response.xpath('//input[@name="__EVENTVALIDATION"]/@value').extract()[0]
        formdata['__VIEWSTATE'] = response.xpath('//input[@name="__VIEWSTATE"]/@value').extract()[0]
        formdata['__EVENTTARGET'] = ''
        formdata['ctl00$ScriptManager1'] = ''
        formdata['ctl00$ContentMain$product_details1$dd_quantity'] = '1'
        formdata['ctl00$ContentMain$product_details1$imgbtn_addToBasket.x'] = '0'
        formdata['ctl00$ContentMain$product_details1$imgbtn_addToBasket.y'] = '0'

        req = FormRequest.from_response(response, formname='aspnetForm', formdata=formdata,
                                        callback=self.parse_shipping1)
        yield req

    def parse_shipping1(self, response):
        req = Request("http://www.chelseamegastore.com/stores/chelsea/en/basket/basket?atb=True?cur=GBP", dont_filter=True,
                      callback=self.parse_shipping2)
        yield req

    def parse_shipping2(self, response):
        shipping_cost = response.xpath('//select[contains(@id, "shippingMethods")]/option/text()').re('(\d+\.\d+)')
        try:
            self.shipping_cost = extract_price(shipping_cost[0]) * self.exchange_rate
            self.logger.info('Shipping cost is %s' % self.shipping_cost)
        except IndexError:
            self.logger.error('No shipping cost parsed from basket. Spider will be closed')
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        categories = response.xpath('//div[contains(@class,"facetCategory")]//a/@href').extract()
        categories += response.xpath('//a[h3[@class="kbFont"]]/@href').extract()
        categories += response.css('.kitMenu a::attr(href)').extract()
        categories += response.xpath('//a/@href[contains(., "/shop-by-player/")]').extract()
        for url in categories:
            yield Request(response.urljoin(url))

        show_all = response.xpath('//a[@id="ctl00_ContentMain_product_browse1_lv_pagingTop_lb_viewAll"]')
        if show_all:
            formdata = dict()
            formdata['__VIEWSTATEGENERATOR'] = response.xpath('//input[@name="__VIEWSTATEGENERATOR"]/@value').extract()[0]
            formdata['__EVENTVALIDATION'] = response.xpath('//input[@name="__EVENTVALIDATION"]/@value').extract()[0]
            formdata['__EVENTTARGET'] = 'ctl00$ContentMain$product_browse1$lv_pagingTop$lb_viewAll'
            formdata['ctl00$ScriptManager1'] = ('ctl00$ContentMain$product_browse1$up_Product_Browse|'
                                                'ctl00$ContentMain$product_browse1$lv_pagingTop$lb_viewAll')

            req = FormRequest.from_response(response,
                                            formname='aspnetForm',
                                            formdata=formdata,
                                            dont_filter=True,
                                            meta=response.meta)

            req.headers['User-Agent'] = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:40.0) Gecko/20100101 Firefox/40.0'
            req.headers['X-MicrosoftAjax'] = 'Delta=true'
            req.headers['X-Requested-With'] = 'XMLHttpRequest'
            yield req

        products = response.xpath('//div[@class="productListLink"]//a[contains(@id,"ProductLink")]/@href').extract()
        for url in products:
            url = add_or_replace_parameter(url, 'cur', 'GBP')
            yield Request(response.urljoin(url),
                          callback=self.parse_product)

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        loader.add_value('category', 'Kits')
        base_data = response.xpath('//script/text()').re('product\w{6} =(.+?});var')
        hero_data = response.xpath('//script/text()').re('product\d{7} =(.+?});var')
        if base_data:
            base_data = json.loads(base_data[0])
        if hero_data:
            hero_data = [json.loads(elem) for elem in hero_data]
            selected_hero = response.xpath('//select[contains(@class,"heroShirts")]/option[@selected]/@value').extract_first()
            if selected_hero:
                hero_data = {elem['ProductID']: elem for elem in hero_data}[int(selected_hero)]
            else:
                hero_data = hero_data[0]
        else:
            hero_data = {}

        if not base_data and not hero_data:
            return
        loader.add_value('name', base_data['Description'])
        loader.add_xpath('sku', '//script/text()', re='sku":"(.+?)"')
        if base_data['Brand']:
            loader.add_value('brand', base_data['Brand']['Name'].title())
        loader.add_value('image_url', response.urljoin(base_data['ImageURL']))
        product = loader.load_item()
        # Player names
        player_from_name = re.search('with *([\w\ \.\-]+?) (\d+)', hero_data.get('Description', ''), re.UNICODE)
        if player_from_name:
            player, number = player_from_name.groups()

        for data in [hero_data, base_data]:
            for variation in data.get('Variations', []):
                size = variation['Description']
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value(None, product)
                loader.replace_value('identifier', variation['VariationId'])
                option_name = data['Description'] + u' ' + size
                loader.replace_value('name', option_name)
                loader.replace_value('price', Decimal(str(variation['PriceActual']))*self.exchange_rate)
                if data.get('ImageURL'):
                    loader.replace_value('image_url', response.urljoin(base_data['ImageURL']))
                if not variation['IsInStock']:
                    loader.replace_value('stock', 0)
                identifier = str(variation['VariationId'])
                item = loader.load_item()
                if self.free_delivery_over is not None and self.free_delivery_over > item['price']:
                    loader.add_value('shipping_cost', self.shipping_cost)
                if item['identifier'] not in self.extracted_identifiers:
                    self.extracted_identifiers.append(item['identifier'])
                    if player_from_name and data == hero_data:
                        item['metadata'] = {
                            'player': player,
                            'number': number,
                            'size': size}
                    else:
                        item['metadata'] = {'size': size}
                    yield item
                # Badges
                printings = {elem['PrintingTypeID']: elem for elem in base_data['printingitems'] if 'New Premier League Player Badges' not in elem['PrintingDescription']}
                printing = printings.get(3)
                if printing:
                    loader = ProductLoader(item=Product(), response=response)
                    loader.add_value(None, item)
                    option_name = loader.get_output_value('name') + u' ' + printing['PrintingDescription']
                    loader.replace_value('name', option_name)
                    price = Decimal(str(variation['PriceActual'])) + Decimal(str(printing['PriceActual']))
                    loader.replace_value('price', format_price(price)*self.exchange_rate)
                    identifier += '-' + str(printing['PrintingID'])
                    loader.replace_value('identifier', identifier)
                    item = loader.load_item()
                    if self.free_delivery_over is not None and self.free_delivery_over <= item['price']:
                        item['shipping_cost'] = '0.00'
                    if item['identifier'] not in self.extracted_identifiers:
                        self.extracted_identifiers.append(item['identifier'])
                        if player_from_name and data == hero_data:
                            item['metadata'] = {
                                'player': player,
                                'number': number,
                                'size': size}
                        else:
                            item['metadata'] = {'size': size}
                        yield item
 

"""
Original ticket: https://app.assembla.com/spaces/competitormonitor/tickets/4947
Extract all items from the Football kits category
Updated for http://www.chelseamegastoreusa.com/ site
"""

import copy
import json
from decimal import Decimal, ROUND_DOWN
import re
import os
import csv

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request, FormRequest
from scrapy import Item, Field
from scrapy.utils.url import add_or_replace_parameter

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price
from kitbagitems import KitBagMeta

def format_price(price, rounding=None):
    if price is None:
        return Decimal('0.00')

    return price.quantize(Decimal('0.01'), rounding=rounding or ROUND_DOWN)

HERE = os.path.abspath(os.path.dirname(__file__))

from scrapy.utils.response import open_in_browser
from scrapy.exceptions import CloseSpider

class ChelseaMegaStore(CrawlSpider):
    name = 'kitbag_us-chelseamegastore.com'
    allowed_domains = ['chelseamegastoreusa.com',
                       'chelsea.custhelp.com']
    start_urls = ['http://www.chelseamegastoreusa.com/Chelsea_Kits',
                  'http://www.chelseamegastoreusa.com/Chelsea_Jerseys',
                  'http://www.chelseamegastoreusa.com/Chelsea_Men',
                  'http://www.chelseamegastoreusa.com/Chelsea_Women',
                  'http://www.chelseamegastoreusa.com/Chelsea_Kids']

    categories = LinkExtractor(restrict_css='div.ShopFor, div.Style, div.CustomShop')
    pages = LinkExtractor(restrict_css='div.topPager')
    products = LinkExtractor(restrict_css='div.Item')
    
    rules = (Rule(pages),
             Rule(products, callback='parse_product'))

    def start_requests(self):
        self.players = []
        with open(os.path.join(HERE, 'Chelsea.csv')) as f:
            reader = csv.reader(f)
            for row in reader:
                self.players.append(row)
                
        yield Request('https://chelsea.custhelp.com/app/answers/detail/a_id/815',
                      callback=self.parse_shipping_us)

    def parse_shipping_us(self, response):
        self.shipping_cost = response.xpath('//td[contains(., "Base Rate")]/../following-sibling::tr[1]/td[2]/p/strong/text()').extract_first()
        for url in self.start_urls:
            yield Request(url)
            
    def parse_shipping(self, response):
        formdata = {}
        formdata['__VIEWSTATEGENERATOR'] = response.xpath('//input[@name="__VIEWSTATEGENERATOR"]/@value').extract()[0]
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
        req = Request("http://www.chelseamegastore.com/stores/chelsea/en/basket/basket?atb=True&cur=USD", dont_filter=True,
                      callback=self.parse_shipping2)
        yield req

    def parse_shipping2(self, response):
        shipping_cost = response.xpath('//select[contains(@id, "shippingMethods")]/option/text()').re('(\d+\.\d+)')
        try:
            self.shipping_cost = extract_price(shipping_cost[0])
            self.logger.info('Shipping cost is %s' % self.shipping_cost)
        except IndexError:
            self.logger.error('No shipping cost parsed from basket. Spider will be closed')
        for url in self.start_urls:
            yield Request(url)

    def parse_product(self, response):
        try:
            identifier = response.xpath('//*[@id="data-product-id"]/@value').extract_first()
        except:
            open_in_browser(response)
            raise CloseSpider()
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
            loader.add_value('shipping_cost', self.shipping_cost)
            option_item = loader.load_item()
            metadata = KitBagMeta()
            metadata['size'] = sub_name
            players = [player for player in self.players if player[0].decode('latin-1') in option_item['name']]
            if players:
                metadata['player'] = players[0][0].decode('latin-1')
                metadata['number'] = players[0][1]
            elif 'Custom' in option_item['name']:
                metadata['player'] = 'Williams'
                metadata['number'] = '10'
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
            loader.add_value('shipping_cost', self.shipping_cost)
            option_item = loader.load_item()
            players = [player for player in self.players if player[0].decode('latin-1') in option_item['name']]
            if players:
                metadata['player'] = players[0][0].decode('latin-1')
                metadata['number'] = players[0][1]
                option_item['metadata'] = metadata
            elif 'Custom' in option_item['name']:
                metadata['player'] = 'Williams'
                metadata['number'] = '10'
                option_item['metadata'] = metadata
            yield option_item

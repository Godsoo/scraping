# -*- coding: utf-8 -*-

"""
Account: Kitbag
Name: kitbag-kitbag.com
Ticket: https://app.assembla.com/spaces/competitormonitor/tickets/4931
"""

import os
import csv
import json
from time import time
from decimal import Decimal
import paramiko
from scrapy import Spider, Request, FormRequest
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.utils.url import add_or_replace_parameter
from scrapy.exceptions import CloseSpider
from product_spiders.items import (
    Product,
    ProductLoaderWithoutSpaces as ProductLoader,
)
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT


HERE = os.path.dirname(os.path.abspath(__file__))


class KitBagSpider(Spider):
    name = u'kitbag-kitbag.com'
    allowed_domains = ['kitbag.com']
    start_urls = ['http://www.kitbag.com/stores/kitbag/en?cur=GBP']

    FREE_DELIVERY_OVER = Decimal('60')
    STANDARD_DELIVERY = None
    DEFAULT_IMG_PARAMS = 'width=400&height=400&quality=95'

    proxy_service_ignore = 'http://85.%|http://89.%|http://86.%'

    items = set()
    shipping_cost_request = None

    cookies = {'KB_44_PriceZoneID': '3',
               'Kitbag_T36_NoFreeDelivery': 'False',
               'KB_44_Currency': 'GBP',
               'KB_44_CurrencyId': '1',
               'KB_44_LocationID': '204',
               'KB_44_LocationISO2': 'GB',
               'KB_44_Language': '1',
               'KB_44_network': 'KITBAG'}

    def __init__(self, *args, **kwargs):
        super(KitBagSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.idled, signals.spider_idle)

    def parse(self, response):
        cookies = response.headers.getlist('Set-Cookie')
        cookies = [c for c in cookies if 'KB_44_BasketID' in c]
        cookies = [c for c in cookies[0].split(';') if 'KB_44_BasketID' in c]
        basket_id = cookies[0].split('=')[1]
        self.cookies['KB_44_BasketID'] = basket_id
        self.logger.info('BasketID is %s' %basket_id)

        yield Request('http://www.kitbag.com/stores/kitbag/en/product/adidas-uefa-champions-league-finale-2016-miniball---white-vapour-steel-tech-green/175807',
                      callback=self.parse_shipping2, priority=10)
        
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = 'gtX34aJy'
        username = 'kitbag'
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        file_path = os.path.join(HERE, 'kitbag_uk_products.csv')
        sftp.get('kitbag_uk_products.csv', file_path)

        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield Request('http://www.kitbag.com/stores/kitbag/en/search/%(PID)s' % row,
                              dont_filter=True,
                              callback=self.parse_search,
                              cookies=self.cookies,
                              meta={'search': {
                                  'pid': row['PID'].decode('unicode_escape').strip(),
                                  'vid': row['VID'].decode('unicode_escape').strip(),
                                  'sku': row['SKU VID'].decode('unicode_escape').strip(),
                                  'player': row['HERO NAME'].decode('unicode_escape').lower().strip(),
                                  'number': row['HERO NUMBER'].decode('unicode_escape').strip(),
                                  'size': row['Size Description'].decode('unicode_escape').strip(),
                                  'brand': row['Merret Department'].decode('unicode_escape').strip(),
                                  'name': row['Product Description'].decode('unicode_escape').strip(),
                              }})

    def parse_shipping2(self, response):
        self.get_shipping_cost(response)

    def parse_search(self, response):
        if 'aspxerrorpath' in response.url:
            yield Request(response.request.meta['redirect_urls'][0], self.parse_search, dont_filter=True, meta=response.meta)
            return
        products = response.xpath('//div[@class="productListItem"]/div[@class="productListLink"]'
                                  '/a/@href').extract()
        for url in products:
            meta = response.meta.copy()
            meta['dont_merge_cookies'] = True
            req = Request(add_or_replace_parameter(response.urljoin(url), 'cur', 'GBP'),
                          callback=self.parse_product,
                          cookies=self.cookies,
                          meta=meta,
                          dont_filter=True)
            yield req

        if not products:
            row = response.meta['search']
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', row['pid'] + 'x' + row['vid'])
            loader.add_value('sku', row['sku'])
            loader.add_value('url', response.url)
            loader.add_value('brand', row['brand'])
            name = row['name']
            is_size_in_name = name.lower().strip().endswith(row['size'].lower())
            if row['player'] and row['player'].lower() != 'n/a':
                name += ' ' + row['player']
            if row['size'] and row['size'].lower() != 'n/a' and not is_size_in_name:
                name += ' - ' + row['size']
            loader.add_value('name', name)
            loader.add_value('price', '0.0')
            loader.add_value('stock', 0)
            item = loader.load_item()
            item['metadata'] = {'size': row['size'], 'player': row['player'], 'number': row['number'],
                                'vid': row['vid'], 'pid': row['pid']}
            yield item

    def parse_product(self, response):
        if 'aspxerrorpath' in response.url:
            yield Request(response.request.meta['redirect_urls'][0], self.parse_product, dont_filter=True, meta=response.meta)
            return
        row = response.meta['search']

        try:
            js_data = response.xpath('//script[contains(text(), "productdetail") or contains(text(), "selectordetails = ")]/text()')\
                .extract()[0]
            js_data = js_data.split(';')
        except:
            js_data = None
        else:
            if row['player'] != 'n/a':
                js_data = filter(lambda s: row['player'] in s.lower() and row['number'] in s, js_data)
            else:
                try:
                    default_opt = response.xpath('//select[@id="ctl00_ContentMain_kit_selector1_product_'
                        'selector1_dd_heroShirt"]/option[@selected]/text()').extract()[0]
                    js_data = filter(lambda s: default_opt.lower() in s.lower(), js_data)
                except:
                    js_data = filter(lambda d: 'var product' in d, js_data)

        if js_data:
            data = json.loads(js_data[0].split(' = ')[-1])
            if row['size']:
                opt = filter(lambda v: v['Description'].lower() == row['size'].lower(), data['Variations'])
                if opt:
                    opt = opt[0]
                    loader = ProductLoader(item=Product(), response=response)
                    loader.add_value('identifier', row['pid'] + 'x' + row['vid'])
                    loader.add_value('sku', row['sku'])
                    loader.add_value('url', response.url)
                    loader.add_value('brand', row['brand'])
                    name = data['Description']
                    is_size_in_name = name.lower().strip().endswith(row['size'].lower())
                    if row['player'] and row['player'].lower() != 'n/a':
                        name += ' ' + row['player']
                    if row['size'] and row['size'].lower() != 'n/a' and not is_size_in_name:
                        name += ' - ' + row['size']
                    loader.add_value('name', name)
                    if not opt['IsInStock']:
                        loader.add_value('stock', 0)
                    loader.add_value('price', opt['PriceActual'])
                    loader.add_value('image_url', response.urljoin(data['ImageURL']))

                    item = loader.load_item()
                    item['metadata'] = {'size': row['size'], 'player': row['player'], 'number': row['number'],
                                        'vid': row['vid'], 'pid': row['pid']}

                    if item['price'] >= self.FREE_DELIVERY_OVER:
                        item['shipping_cost'] = 0
                        yield item
                    else:
                        self.items.add(item)
                        if not response.css('select.pdSizes, select.sizes') and not self.shipping_cost_request:
                            self.logger.debug('Saving product to add to basket for the shipping cost %s' % response.url)
                            self.get_shipping_cost(response)

        else:
            printing_price = None
            js_data = response.xpath(
                '//script[contains(text(), "productdetail") or contains(text(), "selectordetails = ")]/text()') \
                .extract()
            js_data = js_data[0].split(';') if js_data else []
            js_data = filter(lambda d: 'var product' in d, js_data)
            if js_data:
                data = json.loads(js_data[0].split(' = ')[-1])
                if data.get('printingitems'):
                    pr_items = [it for it in data.get('printingitems') if it['PrintingTypeID'] == 1]
                    printing_price = Decimal('0')
                    for pr_item in pr_items:
                        printing_price += Decimal(str(pr_item['PriceActual']))

            try:
                name = response.xpath('//div[@class="selectorProductTitle"]/span/text()').extract()[0].strip()
            except:
                try:
                    name = response.xpath('//*[@itemprop="name"]/text()').extract()[0].strip()
                except:
                    url = response.url
                    if 'redirect_urls' in response.meta:
                        url = response.meta['redirect_urls'][0]
                    retry_no = int(response.meta.get('retry_no', 0))
                    if retry_no < 10:
                        retry_no += 1
                        new_meta = response.meta.copy()
                        new_meta['retry_no'] = retry_no
                        yield Request(add_or_replace_parameter(url, 'cur', 'GBP'), dont_filter=True,
                                      meta=new_meta,
                                      callback=self.parse_product)
                    else:
                        self.log('Max number of retries reached for => %s' % url)
                    return
            try:
                price = response.xpath('//*[@itemprop="price"]/text()').re(r'[\d\.,]+')[0]
            except:
                price = response.xpath('//span[@id="ctl00_ContentMain_kit_selector1_product_selector1_lbl_totalPrice"]/text()').re(r'[\d\.,]+')
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', row['pid'] + 'x' + row['vid'])
            loader.add_value('sku', row['sku'])
            loader.add_value('url', response.url)
            loader.add_value('brand', row['brand'])
            name = row['name']
            is_size_in_name = name.lower().strip().endswith(row['size'].lower())
            if row['player'] and row['player'].lower() != 'n/a':
                name += ' ' + row['player']
            if row['size'] and row['size'].lower() != 'n/a' and not is_size_in_name:
                name += ' - ' + row['size']
            loader.add_value('name', name)
            in_stock = bool(response.xpath('//ul[@id="ksStockDeliveryMessages" or @id="pdStockDeliveryMessages"]//'
                'li[contains(text(), "In Stock Today")]'))
            if not in_stock:
                loader.add_value('stock', 0)
            loader.add_value('price', price)
            try:
                try:
                    image_url = response.urljoin(response.xpath('//img[@itemprop="image"]/@src')\
                        .extract()[0]).split('?')[0]
                except:
                    image_url = response.urljoin(response.xpath('//img[@id="ctl00_ContentMain_'
                        'RecentlyViewed_lv_prods_ctrl0_ProductInfo_ProductImg"]/@src')\
                        .extract()[0]).split('?')[0]
                image_url += '?' + self.DEFAULT_IMG_PARAMS
                loader.add_value('image_url', image_url)
            except:
                pass
            item = loader.load_item()
            if row['player'] and row['player'].lower() != 'n/a' and printing_price:
                item['price'] += printing_price
            item['metadata'] = {'size': row['size'], 'player': row['player'], 'number': row['number'],
                                'vid': row['vid'], 'pid': row['pid']}

            if item['price'] >= self.FREE_DELIVERY_OVER:
                item['shipping_cost'] = 0
                yield item
            else:
                self.items.add(item)
                if not response.css('select.pdSizes, select.sizes') and not self.shipping_cost_request:
                    self.logger.debug('Saving product to add to basket for the shipping cost %s' %response.url)
                    self.get_shipping_cost(response)

    def get_shipping_cost(self, response):
        formdata = dict()
        formdata['ctl00$ContentMain$product_details1$imgbtn_addToBasket.x'] = '0'
        formdata['ctl00$ContentMain$product_details1$imgbtn_addToBasket.y'] = '0'
        self.shipping_cost_request = FormRequest.from_response(response, formdata=formdata, callback=self.parse_shipping_cost, cookies=self.cookies)
        self.shipping_cost_request = self.shipping_cost_request.replace(dont_filter=True)
        return self.shipping_cost_request

    def parse_shipping_cost(self, response):
        shipping_cost = response.xpath('//select[contains(@id, "shippingMethods")]/option/text()').re('(\d+\.\d+)')
        try:
            self.STANDARD_DELIVERY = Decimal(shipping_cost[0])
        except IndexError:
            self.logger.error('No shipping cost parsed. Spider is being closed.')
            raise CloseSpider('No shipping cost parsed')
        self.logger.debug('Shipping cost is %s' %self.STANDARD_DELIVERY)
        for item in self.items:
            if item['price'] < self.FREE_DELIVERY_OVER:
                item['shipping_cost'] = self.STANDARD_DELIVERY
            yield item
        self.items = None

    def idled(self, spider):
        self.log('Spider idle extracting shipping cost')
        if spider.name != self.name or not self.items:
            return
        self.crawler.engine.crawl(self.shipping_cost_request, self)

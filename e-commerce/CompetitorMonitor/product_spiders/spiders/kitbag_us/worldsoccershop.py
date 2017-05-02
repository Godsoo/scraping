# -*- coding: utf-8 -*-
"""
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/4940

The spider crawls two categories: "Shop by club" and "Show by national team".
Collects all options.
"""
import json
import itertools
import re
import os
import csv
from urlparse import urljoin
from decimal import Decimal

from scrapy import Spider, Request
from scrapy.utils.response import get_base_url
from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

option_name_reg = re.compile(r'(.*) \[(.*)\]')

SIZES_DICT = {'xs': 'x small',
              's': 'small',
              'm': 'medium',
              'l': 'large',
              'xl': 'x large',
              '2xl': '2 x large',
              '3xl': '3 x large',
              '4xl': '4 x large ',
              'ys': 'youth small',
              'ym': 'youth medium',
              'yxl': 'youth x large'}

HERE = os.path.abspath(os.path.dirname(__file__))


class WorldSoccerShopSpider(CrawlSpider):
    name = 'kitbag_us-worldsoccershop.com'
    domain = 'worldsoccershop.com'

    start_urls = (
        'http://www.worldsoccershop.com/shop-by-club.html',
        'http://www.worldsoccershop.com/shop-by-national-team.html',
    )
    categories = LinkExtractor(allow=('shop-by-national-team',
                                      'shop-by-club'))
    products = LinkExtractor(restrict_css='.front_item,.product-link')
    players = set()

    rules = (
        Rule(categories),
        Rule(products, callback='parse_product')
    )

    def start_requests(self):
        with open(os.path.join(HERE, 'teams.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['HERO NAME'].lower() != 'n/a' and row['HERO NAME'].lower().strip() != 'williams':
                    self.players.add((row['Merret Department'].decode('utf-8'),
                                      row['HERO NAME'].decode('utf-8'),
                                      row['HERO NUMBER'].decode('utf-8')))
        for url in self.start_urls:
            yield Request(url)

    def parse_product(self, response):
        identifier = response.xpath("//div[@class='item-number']/text()").extract_first()
        sku = identifier
        identifier = re.sub(u'a', u'', identifier, flags=re.IGNORECASE)
        name = response.xpath("//div[@class='product-title']/h1/text()").extract_first().strip()
        price = response.xpath("//div[@class='price']//span[@class='disc-price']/text()").extract()
        if not price:
            price = response.xpath("//div[@class='price']/div[@class='regular-price']/span[@class]/text()").extract()
        if price:
            price = price[0].strip('$').replace(",", "")
        else:
            price = '0.00'
        price = Decimal(price)
        # convert using xe.com
        image_url = response.xpath("//a[@id='mainImage']/img/@src").extract_first()
        categories = response.xpath('//div[@id="breadcrumbs-"]/ul/li/a//text()')[1:-1].extract()
        try:
            brand = response.xpath('//b[contains(., "BRAND:")]/following-sibling::text()[1]').extract_first().title()
        except AttributeError:
            brand = ''

        attributes = response.xpath('//fieldset[@class="attributes"]//li')
        options = []
        option_names = {}
        for option in response.xpath('//select[@name="attrValue_1"]/option[@value!=""]'):
            opt_val = option.xpath('./@value').extract()
            opt_name = option.xpath('./span/text()').extract()
            if opt_val and opt_name:
                option_names[opt_val[0]] = opt_name[0]
        for attr in attributes:
            attr_name = attr.xpath('.//input[@name="attrName_1"]/@value').extract()
            if attr_name:
                attr_name = attr_name[0]
            else:
                continue
            attr_options = []
            attr_values = attr.xpath('.//select/option[@value!=""]/@value').extract()
            for attr_value in attr_values:
                attr_options.append((attr_name, attr_value))
            if not attr_values:
                attr_value = attr.xpath('.//input[@name="attrValue_1"]/@value')[0].extract()
                attr_options.append((attr_name, attr_value))
            if attr_options:
                options.append(attr_options)
        options = itertools.product(*options)
        items = []
        for option in options:
            opt = [option_names.get(v, '') for _, v in option]
            opt = [o for o in opt if o]
            option_name = ' '.join(opt).strip()
            opt = [SIZES_DICT.get(o.lower(), o) for o in opt if o]
            option_id = ':'.join(opt).strip()

            option_name = re.sub('size', '', option_name, flags=re.IGNORECASE).strip()
            size = option_names.get(option[-1][-1], '') if option and option[-1] else ''
            size = re.sub('size', '', size, flags=re.IGNORECASE).strip()
            if option_name:
                product_name = name + ' (' + option_name + ')'
            else:
                product_name = name
            if option_id:
                product_identifier = identifier + u':' + option_id.strip().lower()
            else:
                product_identifier = identifier

            loader = ProductLoader(Product(), option)
            loader.add_value('name', product_name)
            loader.add_value('url', response.url)
            loader.add_value('identifier', product_identifier)
            loader.add_value('sku', sku)
            loader.add_value('price', price)
            loader.add_value('image_url', image_url)
            loader.add_value('brand', brand)
            for category in categories:
                loader.add_value('category', category)

            product = loader.load_item()
            product['metadata'] = {'size': SIZES_DICT.get(size.lower(), size).title()}
            player = [p for p in self.players if p[1].lower() in product_name.lower()]
            if player:
                product['metadata']['player'] = player[0][1].title()
                product['metadata']['number'] = player[0][2]

            item = {'item': product}
            item['attributes'] = ()
            for k, v in option:
                item['attributes'] += ((k, v),)
            items.append(item)

        if not options:
            loader = ProductLoader(Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('url', response.url)
            loader.add_value('identifier', identifier)
            loader.add_value('sku', sku)
            loader.add_value('price', price)
            loader.add_value('image_url', image_url)
            loader.add_value('brand', brand)
            for category in categories:
                loader.add_value('category', category)

            product = loader.load_item()
            product['metadata'] = {}
            player = [p for p in self.players if p[1].lower() in name.lower()]
            if player:
                product['metadata']['player'] = player[0][1].title()
                product['metadata']['number'] = player[0][2]

            item = {'item': product}
            item['attributes'] = ()
            item['attributes'] += ((response.xpath('//input[@name="attrName_1"]/@value')[0].extract(),
                                    response.xpath('//input[@name="attrValue_1"]/@value')[0].extract()),)
            item['attributes'] += ((response.xpath('//input[@name="attrName_1"]/@value')[1].extract(),
                                    response.xpath('//input[@name="attrValue_1"]/@value')[1].extract()),)
            items.append(item)
        product_id = response.xpath('//input[@name="productId"]/@value')[0].extract()
        yield Request('http://www.worldsoccershop.com/InventoryCheck.json?productId={}'.format(product_id),
                      meta={'items': items},
                      callback=self.parse_stock)

    def parse_stock(self, response):
        data = json.loads(response.body)
        for item in response.meta.get('items'):
            attributes = item.get('attributes')
            it = item.get('item')
            for p in data.get('productItems'):
                correct = True
                for attr in attributes:
                    if p['attributes'].get(attr[0], '') != attr[1]:
                        correct = False
                        break
                if correct and 'out' in p['displayText'].lower():
                    it['stock'] = 0
                    break
            yield self.add_shipping_cost(it)

    def add_shipping_cost(self, product):
        product['shipping_cost'] = '12.99'
        return product

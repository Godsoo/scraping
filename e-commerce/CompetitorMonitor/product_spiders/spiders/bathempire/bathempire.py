# -*- coding: utf-8 -*-

import re
import os
from urllib import quote
from scrapy.spider import BaseSpider
try:
    from scrapy.selector import Selector
except ImportError:
    from scrapy.selector import HtmlXPathSelector as Selector

from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc

from scrapy.item import Item, Field
from product_spiders.utils import extract_price
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)


HERE = os.path.abspath(os.path.dirname(__file__))


class MetaData(Item):
    Promotions = Field()
    corner_promotion = Field()


class BathEmpireSpider(BaseSpider):
    name = "bathempire-bathempire.com"
    allowed_domains = ["soak.com", "fsm.attraqt.com"]
    start_urls = ['http://www.soak.com/']

    def parse(self, response):
        categories = response.xpath('//div[@id="header"]//a/@href').extract()
        categories += response.xpath('//div[@class="categorypage"]//div/a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url))

        category_tree = re.findall("'categorytree', '(.*)'\);", response.body)
        category_conf = re.findall("'category', '(.*)'\);", response.body)

        if category_conf and category_tree:
            category_tree = category_tree[0]
            category_conf = category_conf[0]
    
            products_page = ('http://fsm.attraqt.com/zones-js.aspx?version=2.23.2&'
                            'siteId=4170eb3b-f55c-40d3-aaeb-8cb777e96a28&referrer=&'
                            'sitereferrer=&pageurl='+quote(response.url)+'&esp_pg=1&zone0=category_recs1&'
                            'zone1=category&zone2=banner_advert&zone3=category_recs2&'
                            'zone4=category_recs3&facetmode=data&mergehash=true&'
                            'config_categorytree='+category_tree+'&config_category='+category_conf)
            meta={'category_tree': category_tree, 
                  'category_conf': category_conf,
                  'url': response.url}
            yield Request(products_page, callback=self.parse_products, meta=meta)

    def parse_products(self, response):
        base_url = 'http://soak.com'

        hxs = Selector(text=response.body.replace('\\"', '"'))
        
        products = hxs.select('//div[contains(@class, "product")]//a[div[@class="name"]]/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        pages = hxs.select('//a[contains(@class, "pageNumber")]/text()').extract()
        for page in pages:
            next_page = ('http://fsm.attraqt.com/zones-js.aspx?version=2.23.2&'
                         'siteId=4170eb3b-f55c-40d3-aaeb-8cb777e96a28&referrer=&'
                         'sitereferrer=&pageurl='+response.meta['url']+'%23esp_pg%3D'+page+'&zone0=category_recs1&'
                         'zone1=category&zone2=banner_advert&zone3=category_recs2&'
                         'zone4=category_recs3&facetmode=data&mergehash=true&'
                         'config_categorytree='+response.meta['category_tree']+'&config_category='+response.meta['category_conf'])
            yield Request(next_page, callback=self.parse_products, meta=response.meta)

    def parse_product(self, response):
        products = response.xpath('//div[contains(@class, "product")]//a[div[@class="name"]]/@href').extract()
        if products:
            for product in products:
                yield Request(response.urljoin(product), callback=self.parse_product)

            pages = response.xpath('//a[contains(@class, "pageNumber")]/text()').extract()
            for page in pages:
                page = response.urljoin(page)
                yield Request(page)

            return

        name = response.xpath('//div/h1/text()').extract()
        try:
            price = response.xpath('//div[@class="bigprice GBP"]/@data-price').extract()[0]
        except IndexError:
            for p in self.parse(response):
                yield p
            return

        brand = ''
        categories = response.xpath('//ul[@class="breadcrumb"]/li/a/text()').extract()[1:]

        l = ProductLoader(item=Product(), response=response)

        image_url = response.xpath('//div[@id="mainImage"]/img/@src').extract()
        image_url = response.urljoin(image_url[0]) if image_url else ''
        l.add_value('image_url', image_url)
        l.add_value('url', response.url)
        l.add_value('name', name)
        l.add_value('price', extract_price(price))
        l.add_value('brand', brand)
        l.add_value('category', categories)
        sku = response.xpath('//p[@class="partcode"]/text()').re('Quick Code: (.*)')
        sku = sku[0] if sku else ''
        l.add_value('sku', sku)
        l.add_xpath('identifier', '//input[@name="product_id"]/@value')

        item = l.load_item()

        promotions = response.xpath('//div[contains(@class, "price_box")]//div[@class="GBP"]/span[@class="desktop_rrp" or @class="saving"]/text()').extract()

        corner_promotion = response.xpath('//img[@class="cornerflash"]/@src').re('Empire/(.*).png')
        corner_promotion = corner_promotion[0] if corner_promotion else ''

        corner_promotions = {'pricedrop': 'Price Drop',
                             'deal': 'Deal',
                             'freedel': 'Free Delivery',
                             'newarrival': 'New Arrival',
                             'sale': 'Sale',
                             'bestseller': 'Bestseller',
                             'wasteincluded': 'Waste Included',
                             'trayincluded': 'Tray Included',
                             'clearance': 'Clearance',
                             'pricedropred': 'Price Drop',
                             'asseenontv': 'As Seen On T.V'}

        metadata = MetaData()
        metadata['corner_promotion'] = corner_promotions.get(corner_promotion, '')
        metadata['Promotions'] = ' '.join(promotions) if promotions else ''
        item['metadata'] = metadata

        stock_url = "http://soak.com/includes/ajax/in_stock.php"
        part_code = response.xpath('//div[contains(@class, "stock_report")]/@data-partcode').extract()[0]
        manufacturers_id = response.xpath('//div[contains(@class, "stock_report")]/@data-manufacturers_id').extract()[0]
        formdata = {'action': 'in_stock',
                    'manufacturers_id': manufacturers_id,
                    'part_code': part_code}

        yield FormRequest(stock_url, formdata=formdata, callback=self.parse_stock, meta={'item': item})

    def parse_stock(self, response):
        item = response.meta['item']
        stock = response.xpath('//*[contains(text(), "In stock")]').extract()
        if not stock:
            item['stock'] = 0

        shipping_url = "http://soak.com/product.php?action=ShippingQuote"
        formdata = {'productID': item['identifier']}
        req = FormRequest(shipping_url, formdata=formdata, callback=self.parse_shipping_cost, meta={'item': item})
        yield req

    def parse_shipping_cost(self, response):
        item = response.meta['item']

        shipping_cost = response.xpath('//span[@class="GBP currency2"]/text()').extract()
        if shipping_cost:
            item['shipping_cost'] = extract_price(shipping_cost[0])

        yield item


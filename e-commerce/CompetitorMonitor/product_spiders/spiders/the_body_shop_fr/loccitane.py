from __future__ import unicode_literals
from decimal import Decimal
import json

import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price_eu as extract_price


class LoccitaneSpider(BaseSpider):
    name = 'thebodyshop-loccitane_fr'
    allowed_domains = ['fr.loccitane.com']
    start_urls = [
        'http://fr.loccitane.com/beurre-de-karit%C3%A9-certifi%C3%A9-bio--et-contr%C3%B4l%C3%A9-%C3%A9quitable-,74,1,24789,235869.htm', 
        'http://fr.loccitane.com/cr%C3%A8me-mains-karit%C3%A9,74,1,24534,235610.htm', 
        'http://fr.loccitane.com/gel-douche-verveine,74,1,24565,383515.htm', 
        'http://fr.loccitane.com/eau-de-toilette-fleurs-de-cerisier,74,1,24604,500579.htm', 
        'http://fr.loccitane.com/eau-de-toilette-verveine,74,1,24565,383389.htm', 
        'http://fr.loccitane.com/baume-l%C3%A8vres-d%C3%A9lice-de-rose-karit%C3%A9,74,1,24534,618907.htm#s=34000', 
        'http://fr.loccitane.com/bb-cr%C3%A8me-teint-pr%C3%A9cieux-immortelle-spf-30-teinte-pale,74,1,24546,691730.htm#s=57185', 
        'http://fr.loccitane.com/cr%C3%A8me-confort-l%C3%A9g%C3%A8re-karit%C3%A9,74,1,24534,659381.htm#s=24736', 
        'http://fr.loccitane.com/s%C3%A9rum-pr%C3%A9cieux-immortelle,74,1,24546,288455.htm#s=24736', 
        'http://fr.loccitane.com/soin-complet-cade,74,1,24583,274616.htm#s=24736', 
    ]
    data_regex = re.compile('this\.products = ko.observableArray\((.*)\);')
    brand_regex = re.compile('brand: "(.*)",')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        data_json = json.loads(''.join(self.data_regex.findall(response.body_as_unicode())))
        for product in data_json:

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('url', response.url)

            # sku and identifier
            loader.add_value('identifier', product['productId'])
            loader.add_value('sku', product['sku'])

            # name
            name = "{product_name} {product_size}".format(
                product_name=product['title'],
                product_size=product['size']
            )
            loader.add_value('name', name)
            #price
            price = extract_price(product['price'])
            loader.add_value('price', price)
            #stock
            stock = 1
            if not price:
                stock = 0
            loader.add_value('stock', stock)
            #image_url
            loader.add_value('image_url', product['productImageUrl'])
            #brand
            brand = ''.join(self.brand_regex.findall(response.body))
            loader.add_value('brand', brand)
            #category
            loader.add_xpath('category', "//div[@id='breadcrumb']/ul/li[position() > 1 and position() < last()]//text()")
            #shipping_cost
            if price <= 65:
                loader.add_value('shipping_cost', Decimal(4.5))
            else:
                loader.add_value('shipping_cost', Decimal(0))

            return loader.load_item()

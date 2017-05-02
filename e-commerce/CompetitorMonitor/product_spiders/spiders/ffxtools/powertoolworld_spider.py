# -*- coding: utf-8 -*-
import os
import re
import json
from copy import deepcopy
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class PowerToolWorldSpider(BaseSpider):
    name = 'ffxtools-powertoolworld.co.uk'
    allowed_domains = ['powertoolworld.co.uk']
    start_urls = ['http://www.powertoolworld.co.uk/brands']
    brands = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        brands = hxs.select('//*[@id="narrow-by-list2"]//li/a/text()').extract()
        for brand in brands:
            brand = brand.strip()
            if brand != u'':
                self.brands.append(brand.lower())

        categories = hxs.select('//ul[@id="pronav"]//a/@href').extract()
        categories += hxs.select('//ul[@class="subcategories"]//a/@href').extract()
        categories += hxs.select('//dl[@id="narrow-by-list2"]//li/a/@href').extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            yield Request(url)

        products = hxs.select('//h4[@class="product-name"]//a/@href').extract()
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, callback=self.parse_product)

        xnext = hxs.select('//a[@class="next i-next"]/@href').extract()
        if xnext:
            xnext = urljoin_rfc(get_base_url(response), xnext[0])
            yield Request(xnext)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        loader = ProductLoader(item=Product(), response=response)
        name = response.css('.product-name').xpath('h1/text()').extract_first()
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        sname = name.lower()
        for brand in self.brands:
            if sname.startswith(brand):
                loader.add_value('brand', brand.title())
                break
        categories = response.css('.breadcrumbs').xpath('.//a/span/text()').extract()[1:]
        loader.add_value('category', categories)
        sku = hxs.select('//*[@id="product_addtocart_form"]//div[@class="expert-notes "]//span[contains(text(), "SKU: ")]/text()').extract()
        if sku:
            sku = sku[0].replace("SKU: ", '')
        else:
            sku = ''
        loader.add_value('sku', sku)
        identifier = hxs.select('//input[@name="product"]/@value').extract()[0]
        loader.add_value('identifier', identifier+'-new')
        image_url = hxs.select('//img[@id="image-main"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

        price = response.xpath('//script/text()').re('price":"(.+?)"')
        price = extract_price(price[0]) if price else 0 
 
        loader.add_value('price', price)

        in_stock = hxs.select('//div[@class="availability in-stock"]//div[@class="value" and contains(text(), "In stock")]')
        if not in_stock:
            in_stock = hxs.select('//p[@class="availability back-order"]//span[@class="value" and contains(text(), "Back Order")]')

        if not in_stock:
            loader.add_value('stock', 0)

        if loader.get_output_value('price')<100:
            loader.add_value('shipping_cost', 6.50)
       
        item = loader.load_item()

        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            prices = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))
                        prices[product] = prices.get(product, 0) + extract_price(option['price'])
            
            base_price = extract_price(product_data['basePrice'])
            for option_identifier, option_name in products.iteritems():
                option_item = deepcopy(item)

                option_item['identifier'] += '-' + option_identifier
                option_item['name'] += option_name
                option_item['price'] = base_price + prices[option_identifier]
                yield option_item
        else:
            yield item

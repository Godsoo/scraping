"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4476
"""

import json
import itertools
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price

class BuilderDepot(BaseSpider):
    name = 'builderdepot.co.uk'
    allowed_domains = ['builderdepot.co.uk']
    start_urls = ['http://www.builderdepot.co.uk/delivery_information/']
    cookies_enabled = False
    shipping_cost = None

    def parse(self, response):
        shipping_cost = response.xpath('//tr[td[contains(text(),"Standard Large")]]/td[4]/text()').extract()
        if shipping_cost:
            try:
                self.shipping_cost = extract_price(shipping_cost[0])
            except TypeError:
                pass

        for url in response.xpath('//ul[@class="megamenu"]//a/@href').extract():
            if not (url.endswith('pdf') or 'taxswitcher' in url):
                yield Request(response.urljoin(url), callback=self.parse_category)

    def parse_category(self, response):
        for url in response.xpath('//h2[@class="product-name"]/a/@href').extract():
            yield Request(url, callback=self.parse_product)
        for url in response.xpath('//div[@class="pages"]//a/@href').extract():
            yield Request(url, callback=self.parse_category)

    def parse_product(self, response):
        category = response.xpath('//div[@class="breadcrumbs"]//li[position()>1]/a/@title').extract()
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_xpath('sku', '//meta[@itemprop="sku"]/@content')
        loader.add_xpath('url', '//link[@rel="canonical"]/@href')
        loader.add_xpath('name', '//div[@itemprop="name"]/h1/text()')
        loader.add_xpath('price', '//meta[@property="og:product:price:amount"]/@content')
        loader.add_xpath('price', '//span[@id="product-price-%s"]//span[@class="price"]/text()' %loader.get_output_value('identifier'))
        loader.add_value('category', category)
        loader.add_xpath('image_url', '//div[@class="product-img-box"]//img/@src')
        loader.add_xpath('brand', '//meta[@itemprop="brand"]/@content')
        if self.shipping_cost:
            loader.add_value('shipping_cost', self.shipping_cost)
        if not response.xpath('//*[@class="availability in-stock"]'):
            loader.add_value('stock', 0)
        product = loader.load_item()

        if 'Doors, Joinery & Windows' in category:
            product['shipping_cost'] = Decimal('33')
        elif 'Flooring' in category:
            product['shipping_cost'] = Decimal('20')

        config = response.xpath('//script/text()').re('Product.Config\((.+)\);')
        if config:
            data = json.loads(config[0])
            baseprice = Decimal(data['basePrice'])
            options = []
            attributes = data['attributes']
            for attribute_id in attributes:
                options.append(attributes[attribute_id]['options'])
            variants = itertools.product(*options)
            for variant in variants:
                item = Product(product)
                item['price'] = baseprice
                for option in variant:
                    item['identifier'] += '-' + option['id']
                    item['name'] += ' ' + option['label'].strip()
                    item['price'] += Decimal(option['price'])
                    item['price'] *= Decimal('1.2')
                yield Product(item)
            return

        yield product

"""
Account: HealthSpan
Extract all products and options
Original ticket: https://app.assembla.com/spaces/competitormonitor/tickets/5597-healthspan-%7C-naturesbest-%7C-new-site/details
"""
import json
import os
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.http import Request

from product_spiders.items import (Product,
                                   ProductLoaderWithNameStrip as ProductLoader)
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))


class NaturesBestSpider(BaseSpider):
    name = 'healthspan-naturesbest.co.uk'
    allowed_domains = ['www.naturesbest.co.uk', 'naturesbest.co.uk']
    start_urls = ('http://www.naturesbest.co.uk/page/productdirectory/',)

    def parse(self, response):
        categories = response.xpath('//div[@class="leftNAVIGATION"]//a/@href').extract()
        categories += response.xpath('//div[@class="holder_PROMO"]//a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url))
        products = response.xpath('//div[@id="listOfProds"]//a/@href').extract()
        products += response.xpath('//li[@class="prodNAME"]//a/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product)
        next_page = response.xpath('//span[@class="next"]/a[contains(text(),"Next")]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]))
        for prod in self.parse_product(response):
            yield prod

    def parse_product(self, response):
        variants = response.xpath('//script').re('var json_variant = (.*);')
        if variants:
            variants = json.loads(variants[0])
            for json_prod in variants['jsonprod']:
                yield Request(json_prod['json_url'], callback=self.parse_product, meta={'parse_variant': True})

        name = response.xpath('//div[@class="productTITLE"]/h1/text()').extract()
        if not name:
            return
        categories = response.xpath('//div[@itemprop="breadcrumb"]//a/text()')[1:].extract()
        skus = response.xpath('//input[@name="sku"]/@value').extract()
        options = response.xpath('//td[@class="skuname"]/label/text()').extract()
        prices = response.xpath('//td[@class="price"]/text()').extract()
        options_prices = zip(options, skus, prices)
        image_url = response.xpath('//div[@id="innerzoomArea"]//img[@id="productImage"]/@src').extract_first()
        for option, sku, price in options_prices:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('url', response.url)
            option_name = u'{} {}'.format(name[0].strip(), option.strip()).replace(u'\xa0', ' ')
            loader.add_value('name', option_name)
            if image_url:
                loader.add_value('image_url', response.urljoin(image_url))
            loader.add_value('identifier', sku)
            loader.add_value('sku', sku)
            loader.add_value('price', price)
            for cat in categories:
                loader.add_value('category', cat)
            price = extract_price(price)
            if price < Decimal('15.00'):
                loader.add_value('shipping_cost', '1.00')
            in_stock = response.xpath('//link[@itemprop="availability" and contains(@href,"InStock")]')
            if not in_stock:
                loader.add_value('stock', 0)
            yield loader.load_item()

        if response.meta.get('parse_variant'):
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('url', response.url)
            price = response.xpath('//div[@itemprop="price"]/text()').extract()
            loader.add_value('name', name[0].strip())
            if image_url:
                loader.add_value('image_url', response.urljoin(image_url))
            sku = response.xpath('//select[@id="sku_dd"]/option[@selected]/@value').extract_first()
            loader.add_value('identifier', sku)
            loader.add_value('sku', sku)
            loader.add_value('price', price)
            for cat in categories:
                loader.add_value('category', cat)
            price = extract_price(price[0])
            if price < Decimal('15.00'):
                loader.add_value('shipping_cost', '1.00')
            in_stock = response.xpath('//link[@itemprop="availability" and contains(@href,"InStock")]')
            if not in_stock:
                loader.add_value('stock', 0)
            yield loader.load_item()

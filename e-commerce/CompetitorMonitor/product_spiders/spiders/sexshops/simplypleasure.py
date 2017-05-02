# -*- coding: utf-8 -*-
import os
import csv
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy import log

from simplypleasureitem import SimplyPleasureMeta

HERE = os.path.abspath(os.path.dirname(__file__))

class SimplyPleasure(BaseSpider):
    name = 'simplypleasure.co.uk'
    allowed_domains = ['simplypleasure.com']
    start_urls = ('http://www.simplypleasure.com',)
    download_delay = 0
    seen = set()

    cost_prices = {}

    handle_httpstatus_list = [500]

    def start_requests(self):

        with open(HERE+'/absholdings_costprices.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.cost_prices[row['identifier']] = row['cost_price']

        for start_url in self.start_urls:
            yield Request(start_url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[@class="menu"]//a/@href').extract()

        for url in categories:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = hxs.select('//div[@class="pages"][1]//a[contains(@class, "next") '
                               'and @title="Next"][1]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]),
                          callback=self.parse_category)

        products = hxs.select('//div[@class="category-products"]'
                              '//h2[@class="product-name"]/a/@href').extract()
        for product in products:
            product = urljoin_rfc(base_url, product)
            p = product.split('/')[-1]
            if p not in self.seen:
                self.seen.add(p)
                yield Request(product, callback=self.parse_product)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//div[@class="product-name"]/h1/text()').extract()[0]
        url = response.url
        price = hxs.select('//div[@class="product-shop"]//div[@class="wrapper-price-share"]'
                           '//div[@class="price-box"]//span[contains(@id, "product-price")]'
                           '/text()').re('\xa3(.*)')
        if price:
            price = price[0]
        else:
            price = hxs.select('//span[@class="price"]/text()').re('\xa3(.*)')[0]
        sku = hxs.select('//meta[@itemprop="productID"]/@content').re('sku:(.*)')
        category = hxs.select('//div[@class="breadcrumbs"]//a/text()').extract()[-1]
        brand = hxs.select('//div[@class="product-brand"]/img/@src').extract()
        if brand:
            brand = brand[0].split('/')[-1].lower()
            brand = brand.replace('_', ' ').replace('-logo', '#').replace(' logo', '#').split('#')[0].title()
        else:
            brand = ''
        loader.add_value('brand', brand)
        loader.add_value('url', url)
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)
        loader.add_value('category', category)
        stock = hxs.select('//div[@class="pdp-info-icon in-stock"]').extract()
        if not stock:
            loader.add_value('stock', 0)
        image_url = hxs.select('//meta[@property="og:image"]/@content').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])
        options = hxs.select('//div[@class="input-box"]/select')
        main_category = hxs.select('//div[@class="breadcrumbs"]//a/text()').extract()
        main_category = main_category[1] if len(main_category) > 1 else ''
        if options and main_category == 'Essentials':
            log.msg('CRAWL PRODUCT OPTIONS')
            options = json.loads(hxs.extract().partition('Product.Config(')[-1].partition(');')[0])
            #options_number_key = '157'
            #if options_number_key not in options['attributes']:
                #options_number_key = '187'
            options_number_key = response.xpath('//select/@id').re('attribute(\d+)')[0]
            options = options['attributes'][options_number_key]['options']
            for option in options:
                product = loader.load_item()
                product['identifier'] = product['identifier'] + '-' + option['label']
                product['name'] = product['name'] + ' ' + option['label']
                product['price'] = float(product['price']) + float(option['price'])
                option_loader = ProductLoader(item=product, response=response)
                item = option_loader.load_item()
                metadata = SimplyPleasureMeta()
                metadata['cost_price'] = self.cost_prices.get(item['identifier'])
                item['metadata'] = metadata
                yield item
        else:
            item = loader.load_item()
            metadata = SimplyPleasureMeta()
            metadata['cost_price'] = self.cost_prices.get(item['identifier'])
            item['metadata'] = metadata
            yield item

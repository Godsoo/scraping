# -*- coding: utf-8 -*-
"""
Customer: Leader Stores
Website: http://www.oakwooddoors.co.uk
Extract all products, including options that change the price

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4474-leader-stores---new-site---oak-wood-doors/details#

"""

import os
import re
import json
from copy import deepcopy
import itertools

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price

from scrapy import log

from product_spiders.config import DATA_DIR

HERE = os.path.abspath(os.path.dirname(__file__))


class OakWoodDoorsSpider(BaseSpider):
    name = 'leaderstores-oakwooddoors.co.uk'
    allowed_domains = ['oakwooddoors.co.uk']
    start_urls = ['http://www.oakwooddoors.co.uk/']

    def parse(self, response):
        base_url = get_base_url(response)

        categories = response.xpath('//ul[@id="nav"]//a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category))

        products = response.xpath('//a[@class="product-name"]/@href').extract()
        for product in products:
            categories = ''.join(response.xpath('//ul[@itemprop="breadcrumb"]/li/a/text()').extract())
            all_options = False
            if 'EXTERNAL DOORS' in categories or 'INTERNAL DOORS' in categories:
                all_options = True
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product, meta={'all_options': all_options})

        next_page = response.xpath('//a[@class="next i-next"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

    def parse_product(self, response):

        loader = ProductLoader(item=Product(), response=response)
        price = response.xpath('//span[@class="price-including-tax"]/span[@itemprop="price"]/text()').extract()
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        name = response.xpath('//h1/text()').extract()[0].strip()
        loader.add_value('name', name)
        categories = response.xpath('//ul[@itemprop="breadcrumb"]/li/a/text()').extract()[1:]
        loader.add_value('category', categories)
        brand = response.xpath('//tr[th[contains(text(), "Manufacturer")]]/td/text()').extract()
        brand = brand[-1] if brand else ''
        loader.add_value('brand', brand)
        if loader.get_output_value('price')<900:
            loader.add_value('shipping_cost', 39)
        sku = response.xpath('//span[@class="sku"]/text()').extract()[-1].strip()
        loader.add_value('sku', sku)
        stock = response.xpath('//span[@id="stock_av" and contains(text(), "In Stock")]')
        if not stock:
            loader.add_value('stock', 0)
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])
        item = loader.load_item()
        yield item

        options_containers = response.xpath('//select[contains(@name, "options[")]')

        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            prices = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' '.join((products.get(product, ''), option['label']))
                        prices[product] = prices.get(product, 0) + extract_price(option['price'])

            if not options_containers:
                for option_identifier, option_name in products.iteritems():
                    product_option = deepcopy(item)
                    product_option['identifier'] += '-' + option_identifier
                    product_option['name'] += option_name
                    product_option['price'] += prices[option_identifier]
                    if product_option['price'] > item['price'] or response.meta.get('all_options'):
                        yield product_option


        if options_containers:
            combined_options = []
            for options_container in options_containers:
                element_options = []
                for option in options_container.xpath('option[@value!=""]'):
                    option_id = option.xpath('@value').extract()[0]
                    option_name = option.xpath('text()').extract()[0].split(' +')[0]
                    option_price = option.xpath('@price').extract()[0]
                    option_attr = (option_id, option_name, option_price)
                    element_options.append(option_attr)
                combined_options.append(element_options)

            combined_options = list(itertools.product(*combined_options))
            options = []
            for combined_option in combined_options:
                final_option = {}
                for option in combined_option:
                    final_option['desc'] = final_option.get('desc', '') + ' ' + option[1]
                    final_option['identifier'] = final_option.get('identifier', '') + '-' + option[0]
                    final_option['price'] = final_option.get('price', 0) + extract_price(option[2])
                options.append(final_option)

            for option in options:
                product_option = deepcopy(item)
                loader = ProductLoader(response=response, item=Product())
                option_name = option['desc']
                option_identifier = option['identifier']
                product_option['identifier'] += option_identifier
                product_option['name'] += ' ' + option_name
                product_option['price'] = product_option['price'] + option['price']
                if product_option['price']<900:
                    product_option['shipping_cost'] = 39
                if options_config and products:
                    for option_identifier, option_name in products.iteritems():
                        final_option = deepcopy(product_option)
                        final_option['identifier'] += '-' + option_identifier
                        final_option['name'] += option_name
                        final_option['price'] += prices[option_identifier]
                        if final_option['price']<900:
                            final_option['shipping_cost'] = 39
                        if final_option['price'] > item['price'] or response.meta.get('all_options'):
                            yield final_option
                else:   
                    if product_option['price'] > item['price'] or response.meta.get('all_options'):
                        yield product_option

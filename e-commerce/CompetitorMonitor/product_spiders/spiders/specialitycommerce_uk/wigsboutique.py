import os
import re
import json
import csv
import urlparse
import itertools

from copy import deepcopy

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class WigsBoutiqueSpider(BaseSpider):
    name = 'specialitycommerceuk-wigsboutique.co.uk'
    allowed_domains = ['wigsboutique.co.uk']

    start_urls = ['http://www.wigsboutique.co.uk']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ol[@class="nav-primary"]/li/a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_products)    

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        nextp = hxs.select('//a[contains(@class, "next")]/@href').extract()
        if nextp:
            yield Request(urljoin_rfc(base_url, nextp[0]), callback=self.parse_products)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        brand = hxs.select('//span[@itemprop="brand"]/span/text()').extract()
        brand = brand[0] if brand else ''

        product_name = hxs.select('//h1[@itemprop="name"]/text()').extract()
        product_name = product_name[0].strip()
       
        product_price = response.xpath('//meta[@itemprop="price"]/@content').extract_first()

        product_price = extract_price(product_price)
       
        product_code = hxs.select('//div[@class="product-name"]/meta[@itemprop="sku"]/@content').extract()[0]

        image_url = hxs.select('//div[@class="product-img-box"]/div/a/img/@src').extract()
        if not image_url:
            image_url = hxs.select('//div[@id="imageShowcase"]/img/@src').extract()

        image_url = image_url[0] if image_url else ''
        
        categories = hxs.select('//div[@class="breadcrumbs"]/ul/li/a/text()').extract()
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', product_name)
        loader.add_value('url', response.url)
        loader.add_value('sku', product_code)
        loader.add_value('identifier', product_code)
        loader.add_value('brand', brand)
        loader.add_value('shipping_cost', '4.99')
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url))

        for category in categories:
            if category.upper() != 'BRANDS':
                loader.add_value('category', category)

        loader.add_value('price', product_price)

        out_of_stock = hxs.select('//p[@class="availability out-of-stock"]')
        if out_of_stock:
            loader.add_value('stock', 0)

        item = loader.load_item()
        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            option_item = deepcopy(item)
            product_data = json.loads(options_config.groups()[0])
            products = {}
            prices = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))
                        prices[product] = prices.get(product, 0) +  extract_price(option['price'])

            options_containers = hxs.select('//select[contains(@name, "options[")]')
            extra_options = []
            if len(options_containers)>1:
                combined_options = []
                for options_container in options_containers:
                    element_options = []
                    for option in options_containers.select('option[@value!=""]'):
                        option_id = option.select('@value').extract()[0]
                        option_name = option.select('text()').extract()[0]
                        option_price = option.select('@price').extract()[0]
                        option_attr = (option_id, option_name, option_price)
                        element_options.append(option_attr)
                    combined_options.append(element_options)
                    combined_options = list(itertools.product(*combined_options))

                for combined_option in combined_options:
                    final_option = {}
                    for option in combined_option:
                        final_option['desc'] = final_option.get('desc', '') + ' ' + option[1]
                        final_option['identifier'] = final_option.get('identifier', '') + '-' + option[0]
                        final_option['price'] = final_option.get('price', 0) + extract_price(option[2])
                    extra_options.append(final_option)
            else:
                for option in options_containers.select('option[@value!=""]'):
                    final_option = {}
                    final_option['desc'] = ' ' + option.select('text()').extract()[0]
                    final_option['identifier'] = '-' + option.select('@value').extract()[0]
                    final_option['price'] = extract_price(option.select('@price').extract()[0])
                    extra_options.append(final_option)

            product_price = extract_price(product_data['basePrice'])
            for option_identifier, option_name in products.iteritems():
                option_item['identifier'] = product_code + '-' + option_identifier
                option_item['name'] = product_name + option_name
                option_item['price'] = product_price + prices[option_identifier]
                option_item['sku'] = option_item['identifier']
                if extra_options:
                    for extra_option in extra_options:
                        extra_opt_item = deepcopy(option_item)
                        extra_opt_item['identifier'] = extra_opt_item['identifier'] + extra_option['identifier']
                        extra_opt_item['name'] = extra_opt_item['name'] + extra_option['desc']
                        extra_opt_item['price'] =  extra_opt_item['price'] + extra_option['price']
                        extra_opt_item['sku'] = option_item['identifier']
                        yield extra_opt_item
                else:
                    yield option_item
        else:
            yield item

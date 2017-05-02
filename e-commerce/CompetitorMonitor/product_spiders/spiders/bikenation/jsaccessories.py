# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
import re
import json


from scrapy import log


class JsaccessoriesSpider(BaseSpider):
    name = u'jsaccessories.co.uk'
    allowed_domains = ['www.jsaccessories.co.uk']
    start_urls = [
        'http://www.jsaccessories.co.uk/'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        script = re.search('.update\("(.*)\);', response.body).group(1)
        script = script.replace('\\', '')
        hxs = HtmlXPathSelector(text=script)
        for url in hxs.select('//a[@class="itemMenuName level1"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url + '?limit=all'), callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@class="category-products"]//li/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        redirected_urls = response.meta.get('redirect_urls', None)
        if redirected_urls:
            log.msg('Skips product, redirected url: ' + str(redirected_urls[0]))
            return

        image_url = hxs.select('//*[@id="image"]/@src').extract()
        try:
            product_identifier = hxs.select('//input[@name="product"]/@value').extract()[0].strip()
        except:
            product_identifier = hxs.select('//form[@id="product_addtocart_form"]/@action').re(r'/product/(\d+)')[0]
        product_name = hxs.select('//*[@id="js_breadcrumb"]/ul/li[@class="product"]/strong/text()').extract()[0].strip()
        category = hxs.select('//*[@id="js_breadcrumb"]/ul/li[2]/a/text()').extract()
        category = category[0].strip() if category else ''
        brand = hxs.select('//div[@class="product-name"]/h1/text()[1]').extract()
        brand = brand[0].strip() if brand else ''

        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))

            for identifier, option_name in products.iteritems():
                product_loader = ProductLoader(item=Product(), selector=hxs)
                product_loader.add_value('identifier', product_identifier + '_' + identifier)
                product_loader.add_value('name', product_name + option_name)
                if image_url:
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                price = float(product_data['basePrice'])
                product_loader.add_value('price', round(price, 2))
                product_loader.add_value('url', response.url)
                product_loader.add_value('brand', brand)
                product_loader.add_value('category', category)
                product_loader.add_value('shipping_cost', 3)
                product = product_loader.load_item()
                yield product
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('identifier', product_identifier)
            product_loader.add_value('name', product_name)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            price = hxs.select('//*[@id="product-price-{}"]//text()'.format(product_identifier)).extract()
            price = ''.join(price).strip()
            if price == '':
                price = hxs.select('//*[@id="old-price-{}"]//text()'.format(product_identifier)).extract()
                price = ''.join(price).strip()
            price = extract_price(price)
            product_loader.add_value('price', price)
            product_loader.add_value('url', response.url)
            product_loader.add_value('brand', brand)
            product_loader.add_value('category', category)
            product_loader.add_value('shipping_cost', 3)
            product = product_loader.load_item()
            yield product

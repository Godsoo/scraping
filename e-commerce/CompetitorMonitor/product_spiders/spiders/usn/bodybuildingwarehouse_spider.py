# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
import json
import re


class BodybuildingwarehouseSpider(BaseSpider):
    name = u'usn-bodybuildingwarehouse.co.uk'
    allowed_domains = ['bodybuildingwarehouse.co.uk']
    start_urls = ['http://www.bodybuildingwarehouse.co.uk/']

    def start_requests(self):
        brands = {'Optimum Nutrition': 'http://www.bodybuildingwarehouse.co.uk/optimum-nutrition?limit=all',
                  'BSN': 'http://www.bodybuildingwarehouse.co.uk/bsn-supplements?limit=all',
                  'PhD': 'http://www.bodybuildingwarehouse.co.uk/phd-nutrition?limit=all',
                  'Reflex': 'http://www.bodybuildingwarehouse.co.uk/reflex?limit=all',
                  'Cellucor': 'http://www.bodybuildingwarehouse.co.uk/cellucor?limit=all',
                  'USN': 'http://www.bodybuildingwarehouse.co.uk/usn?limit=all'}

        for brand, brand_url in brands.items():
            yield Request(brand_url, meta={'brand': brand})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # products
        for url in hxs.select('//div[@class="category-products"]//li/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        brand = response.meta.get('brand')

        image_url = hxs.select('//p[@class="product-image"]/img/@src').extract()
        try:
            product_identifier = hxs.select('//input[@name="product"]/@value').extract()[0].strip()
        except:
            product_identifier = hxs.select('//form[@id="product_addtocart_form"]/@action').re(r'/product/(\d+)')[0]
        product_name = hxs.select('//div[@class="product-name"]/h1/text()').extract()[0]
        category = hxs.select('//div[@class="breadcrumbs"]//a/span/text()').extract()[2:]
        price = hxs.select('//*[@id="product-price-{}"]/span/text()'.format(product_identifier)).extract()
        if not price:
            price = hxs.select('//*[@id="product-price-{}"]/text()'.format(product_identifier)).extract()
        if not price:
            price = hxs.select('//div[@class="price-box"]/span[@class="price"]/text()').extract()
        if not price:
            return
        price = extract_price(price[0].strip())
        sku = hxs.select('//p[@class="product-ids"]/text()').extract()[0].replace('SKU# ', '')
        out_of_stock = hxs.select('//p[@class="availability out-of-stock"]')

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

            for identifier, option_name in products.iteritems():
                product_loader = ProductLoader(item=Product(), selector=hxs)
                product_loader.add_value('identifier', product_identifier + '_' + identifier)
                product_loader.add_value('name', product_name + option_name)
                if image_url:
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

                product_loader.add_value('price', price + prices[identifier])
                product_loader.add_value('url', response.url)
                product_loader.add_value('brand', brand)
                product_loader.add_value('category', category)
                product_loader.add_value('sku', sku)
                if price < 30:
                    product_loader.add_value('shipping_cost', 2.99)
                if out_of_stock:
                    product_loader.add_value('stock', 0)
                product = product_loader.load_item()
                yield product
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('identifier', product_identifier)
            product_loader.add_value('name', product_name)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            product_loader.add_value('price', price)
            product_loader.add_value('url', response.url)
            product_loader.add_value('brand', brand)
            product_loader.add_value('category', category)
            product_loader.add_value('sku', sku)
            if price < 30:
                    product_loader.add_value('shipping_cost', 2.99)
            if out_of_stock:
                    product_loader.add_value('stock', 0)
            product = product_loader.load_item()
            yield product

# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
import re
import demjson


class PushysSpider(BaseSpider):
    name = u'crc_au-pushys.com.au'
    allowed_domains = ['www.pushys.com.au']
    start_urls = ('http://www.pushys.com.au/', )
    brands = []

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for brand in hxs.select('//*[@id="megamenu"]/li[11]//li[@class="level2"]/a/text()').extract():
            self.brands.append(brand.strip())
        categories = hxs.select('//*[@id="megamenu"]/li/a/span/text()').extract()[2:]
        urls = hxs.select('//*[@id="megamenu"]/li/a/@href').extract()[2:]
        for category, url in zip(categories, urls):
            yield Request(urljoin_rfc(base_url, url + '?limit=72'),
                          callback=self.parse_products_list,
                          meta={'category': category})

    def parse_products_list(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//div[@class="category-products"]//li/a[1]/@href').extract():
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product,
                          meta={'category': response.meta.get('category')})
        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_products_list,
                          meta={'category': response.meta.get('category')})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//*[@id="main-image"]/@href').extract()
        try:
            product_identifier = hxs.select('//input[@name="product"]/@value').extract()[0].strip()
        except:
            product_identifier = hxs.select('//form[@id="product_addtocart_form"]/@action').re(r'/product/(\d+)')[0]
        product_name = hxs.select('//div[@class="product-name"]/h1/text()').extract()[0].strip()
        category = response.meta.get('category')
        sku = hxs.select('//div[@class="sku-package"]/text()').extract()
        if sku:
            sku = sku[0].strip()
            sku = sku.replace('SKU# ', '')
        else:
            sku = ''

        brand = ''
        for b in self.brands:
            if product_name.startswith(b):
                brand = b
                break
        options_config = re.search(r'var spConfig=new Product.Config\((.*)\)', response.body.replace('var spConfig = new', 'var spConfig=new'))
        ean = hxs.select('//div[@class="sku-package" and contains(text(), "SKU# ")]/text()').extract()
        if options_config:
            product_data = demjson.decode(options_config.groups()[0], return_errors=True)[0]
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
                product_loader.add_value('sku', sku)
                product = product_loader.load_item()
                if ean:
                    product['metadata'] = {"ean": ean[0].split("SKU# ")[-1].strip()}
                yield product
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('identifier', product_identifier)
            product_loader.add_value('name', product_name)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            price = hxs.select('//meta[@itemprop="price"]/@content').extract()
            price = ''.join(price).strip()
            if price == '':
                price = hxs.select('//*[@id="old-price-{}"]//text()'.format(product_identifier)).extract()
                price = ''.join(price).strip()
            price = extract_price(price)
            product_loader.add_value('price', price)
            product_loader.add_value('url', response.url)
            product_loader.add_value('brand', brand)
            product_loader.add_value('category', category)
            product_loader.add_value('sku', sku)
            product = product_loader.load_item()
            if ean:
                product['metadata'] = {"ean": ean[0].split("SKU# ")[-1].strip()}
            yield product


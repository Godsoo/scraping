# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from colourbankitems import ColourBankMeta
import re
import json


class WedoBedsCoUkSpider(BaseSpider):
    name = u'wedo-beds.co.uk'
    allowed_domains = ['www.wedo-beds.co.uk']
    start_urls = [
        'http://www.wedo-beds.co.uk/'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        urls = [url for url in hxs.select('//*[@id="anav"]//li/a/@href').extract()
                if url not in ('http://www.wedo-beds.co.uk/checkout/cart/',)]
        urls.append('http://www.wedo-beds.co.uk/beds/types.html')
        urls.append('http://www.wedo-beds.co.uk/beds/size.html')
        urls.append('http://www.wedo-beds.co.uk/mattresses/sizes.html')
        urls.append('http://www.wedo-beds.co.uk/mattresses/types.html')
        urls.append('http://www.wedo-beds.co.uk/mattresses/firmness.html')
        urls.append('http://www.wedo-beds.co.uk/mattresses/brands.html')
        urls.append('http://www.wedo-beds.co.uk/headboards/sizes.html')
        urls.append('http://www.wedo-beds.co.uk/headboards/material.html')
        urls.append('http://www.wedo-beds.co.uk/headboards/styles.html')
        urls.append('http://www.wedo-beds.co.uk/headboards/types.html')

        # menu
        for url in urls:
            yield Request(add_or_replace_parameter(urljoin_rfc(base_url, url), 'limit', 'all'), self.parse_categories_products)

    def parse_categories_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # categories
        for url in hxs.select('//ul[@class="products-grid"]/li/a/@href').extract():
            yield Request(add_or_replace_parameter(urljoin_rfc(base_url, url), 'limit', 'all'),
                          callback=self.parse_categories_products)
        for url in hxs.select('//ul[@class="products-grid"]//a[@class="subcategory-thumbnails-list-element-link"]/@href').extract():
            yield Request(add_or_replace_parameter(urljoin_rfc(base_url, url), 'limit', 'all'),
                          callback=self.parse_categories_products)
        for url in hxs.select('//section//div[@class="editable-type"]/a/@href').extract():
            yield Request(add_or_replace_parameter(urljoin_rfc(base_url, url), 'limit', 'all'),
                          callback=self.parse_categories_products)
        for url in hxs.select('//div[contains(@class, "editable-size")]//a/@href').extract():
            yield Request(add_or_replace_parameter(urljoin_rfc(base_url, url), 'limit', 'all'),
                          callback=self.parse_categories_products)
        # products
        for url in hxs.select('//h2[@class="product-name"]/a/@href|//a[@class="fmore"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//div[@id="product-image-container"]//img[1]/@src').extract()
        if not image_url:
            image_url = hxs.select('//img[@id="product-main-image"]/@src').extract()
        try:
            product_identifier = hxs.select('//input[@name="product"]/@value').extract()[0].strip()
        except:
            product_identifier = hxs.select('//form[@id="product_addtocart_form"]/@action').re(r'/product/(\d+)')[0]
        product_name = hxs.select('normalize-space(//h1[@class="product-title"]/text())').extract()[0]
        category = hxs.select('//nav[@id="breadcrumd_abbotandknight"]//li/a/text()').extract()
        category = category[-1].strip() if category else ''
        brand = ''
        promotion = False
        feature_names = hxs.select('//*[@id="product-attribute-specs"]//td[@class="feature-title"]/text()').extract()
        feature_values = hxs.select('//*[@id="product-attribute-specs"]//td[@class="feature-description"]/text()').extract()
        for name, value in zip(feature_names, feature_values):
            if name.strip() == 'Brand:':
                brand = value.strip()
            elif name.strip() == 'Promotions:' and value.strip() == 'On Sale':
                promotion = True

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
                price = float(product_data['childProducts'][identifier]['finalPrice']) * 1.2
                product_loader.add_value('price', round(price, 2))
                product_loader.add_value('url', response.url)
                product_loader.add_value('brand', brand)
                product_loader.add_value('category', category)
                product = product_loader.load_item()
                if promotion:
                    metadata = ColourBankMeta()
                    metadata['sold_as'] = 'Promotion'
                    product['metadata'] = metadata
                yield product
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('identifier', product_identifier)
            product_loader.add_value('name', product_name)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            price = hxs.select('//*[@id="product-price-{}"]/span/text()'.format(product_identifier)).extract()
            if not price:
                price = hxs.select('//*[@id="product-price-{}"]/text()'.format(product_identifier)).extract()
            if price and price[0].strip() == '':
                price = hxs.select('//*[@id="old-price-{}"]/span/text()'.format(product_identifier)).extract()
            price = extract_price(price[0].strip())
            product_loader.add_value('price', price)
            product_loader.add_value('url', response.url)
            product_loader.add_value('brand', brand)
            product_loader.add_value('category', category)
            product = product_loader.load_item()
            if promotion:
                metadata = ColourBankMeta()
                metadata['sold_as'] = 'Promotion'
                product['metadata'] = metadata
            yield product

        # Related categories
        for url in hxs.select('//div[@id="product-related"]//a/@href').extract():
            yield Request(add_or_replace_parameter(urljoin_rfc(base_url, url), 'limit', 'all'), self.parse_categories_products)

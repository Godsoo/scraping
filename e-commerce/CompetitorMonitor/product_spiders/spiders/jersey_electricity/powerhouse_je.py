# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
import json
from scrapy.utils.url import add_or_replace_parameter
from copy import deepcopy


class PowerhouseJeSpider(BaseSpider):
    name = u'jerseyelectricity-powerhouse.je'
    allowed_domains = ['powerhouse.je']
    start_urls = [
        'http://www.powerhouse.je/'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # categories
        for url in hxs.select('//a[@class="sub_dept_header"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)
        yield Request('http://www.powerhouse.je/brands', callback=self.parse_brands_list)

    def parse_brands_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # brands
        for url in hxs.select('//div[@class="manufacturers_page_alpha"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # products
        for url in hxs.select('//div[@class="product_title"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        # pagination
        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//*[@id="product_medium_image"]/@src').extract()
        product_identifier = hxs.select('//*[@id="parent_product_id"]/@value').extract()[0]
        product_name = hxs.select('//*[@id="product_title"]/text()').extract()[0].strip()
        price = hxs.select('//span[@itemprop="price" and @class="GBP"]/@content').extract()[0]
        price = extract_price(price)
        category = hxs.select('//*[@id="breadcrumb_container"]//a/text()').extract()[1:]
        brand = hxs.select('//*[@id="product_title_brand"]/text()').extract()
        brand = brand[0] if brand else ''
        sku = hxs.select('//*[@id="product_reference"]/text()').extract()
        sku = sku[0] if sku else ''
        in_stock = hxs.select('//span[@class="product_in_stock" and not(@style)]')
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('name', product_name)
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        product_loader.add_value('price', price)
        product_loader.add_value('url', response.url)
        product_loader.add_value('category', category)
        product_loader.add_value('brand', brand)
        product_loader.add_value('sku', sku)
        product_loader.add_value('shipping_cost', 0)
        if not in_stock:
            product_loader.add_value('stock', 0)
        product = product_loader.load_item()
        url = 'http://www.powerhouse.je/ajax/get_product_options/' + product_identifier
        url += '?cmd=addtobasket&parent_product_id={}&product_id=0&image_product_id=0&image_id=0&image_index=0'.format(product_identifier)
        yield Request(url, callback=self.parse_options, meta={'product': product, 'url': url})

    def parse_options(self, response):
        product = response.meta['product']
        data = json.loads(response.body)
        total_attributes = int(data['total_attributes'])
        if total_attributes > 0:
            if total_attributes == 1:
                attribute = data['attributes'][0]
                attribute_id = str(attribute['id'])
                for value in attribute['values']:
                    url = add_or_replace_parameter(response.meta['url'],
                                                   'attributes[' + attribute_id + ']',
                                                   str(value['value_id']))
                    yield Request(url, callback=self.parse_selection, meta={'product': product})
            elif total_attributes == 2:
                attribute = data['attributes'][0]
                attribute_id = str(attribute['id'])
                for value in attribute['values']:
                    url = add_or_replace_parameter(response.meta['url'],
                                                   'attributes[' + attribute_id + ']',
                                                   str(value['value_id']))
                    yield Request(url, callback=self.parse_options2, meta={'product': product})
        else:
            yield product

    def parse_options2(self, response):
        product = deepcopy(response.meta['product'])
        data = json.loads(response.body)
        attribute = data['attributes'][1]
        attribute_id = str(attribute['id'])
        for value in attribute['values']:
            url = add_or_replace_parameter(response.url,
                                           'attributes[' + attribute_id + ']',
                                           str(value['value_id']))
            yield Request(url, callback=self.parse_selection, meta={'product': product})

    def parse_selection(self, response):
        product = deepcopy(response.meta['product'])
        data = json.loads(response.body)
        for selection_id, selection in data['selection'].iteritems():
            product['identifier'] += '_' + str(selection_id)
            product['name'] = selection['title_no_manufacturer']
            product['sku'] = selection['reference']
            product['price'] = extract_price(str(selection['price_breaks'][0]['flat_price_inc']))
            product['stock'] = selection['stock_level']
            yield product

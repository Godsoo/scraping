# -*- coding: utf-8 -*-

import re
import json
from lxml.html import document_fromstring
from urlparse import urljoin
from scrapy.utils.response import get_base_url
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.utils.url import add_or_replace_parameter
from scrapy import log
from product_spiders.items import Product, ProductLoader

from product_spiders.base_spiders.primary_spider import PrimarySpider

#log.start()

class MainmanshopSpider(PrimarySpider):

    name = 'arco_a-mainmanshop.co.uk'
    allowed_domains = ['mainmanshop.co.uk']
    start_urls = ['http://www.mainmanshop.co.uk/']
    xhr_url = 'http://www.mainmanshop.co.uk/qty-check.php?pcode='
    xhr_header = {'X-Requested-With': 'XMLHttpRequest'}
    xpath = {
        'category_link': '//ul[@id="category-menu"]/li/a/@href',
        'subcategory_link': '//ul[@id="inline-product-list"]/li/a/@href',
        'pagination': '//a[@class="next-button"]/@href',
        'prod_listing': '//ul[@id="inline-product-list"]/li/form//h3/a/@href',
        'prod_category': '//div[@class="jssBreadcrumb"]/a[2]/text()',
        'prod_content': '//div[@id="product-content"]',
        'prod_title': './/div[@class="wrap-product-short"]/h2/text()',
        'prod_code': './/div[@class="wrap-product-short"]/h3/text()',
        'prod_price': './/div[@class="currentprice"]//span[contains(@id, "price")]/text()',
        'prod_image': './/div[@class="bigimage"]/img/@src',
    }
    re = {
        'prod_url_id': re.compile(r'/product.php/(\d+)/'),
        'prod_price': re.compile(ur'£([0-9\.]+)'),
        'prod_code': re.compile(
            r'(?P<code>[\w-]+)(?P<option>/\w+)?\s+:\s+(?P<stock>\d+)\s+available'
        ),
        'prod_option': re.compile(
            ur'(?P<option>/?\w+)(?: \(\+£(?P<overprice>[0-9\.]+)\))?'
        ),
    }

    csv_file = 'mainmanshop_crawl.csv'

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select(self.xpath['category_link']).extract()
        if not self._validate_not_empty('categories', categories, response):
            return
        for category_url in categories:
            yield Request(category_url, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        subcategories = hxs.select(self.xpath['subcategory_link']).extract()
        if not self._validate_not_empty('subcategories', subcategories, response):
            return
        for subcategory_url in subcategories:
            yield Request(subcategory_url, callback=self.parse_listing)

        for request in self.parse_listing(response):
            yield request

    def parse_listing(self, response):
        hxs = HtmlXPathSelector(response)
        subcategories = hxs.select(self.xpath['subcategory_link']).extract()
        if subcategories:
            for subcategory_url in subcategories:
                yield Request(subcategory_url, callback=self.parse_listing)
            # return
        products = hxs.select(self.xpath['prod_listing']).extract()
        if not self._validate_not_empty('products', products, response):
            return
        for product_url in products:
            yield Request(product_url, callback=self.parse_product)
        pagination = hxs.select(self.xpath['pagination']).extract()
        if pagination:
            yield Request(pagination[0], callback=self.parse_listing)

    def parse_product(self, response):
        url_id_match = self.re['prod_url_id'].search(response.url)
        if not self._validate_value('URL_ID', url_id_match, response):
            return
        url_id = url_id_match.groups()[0]
        hxs = HtmlXPathSelector(response)
        product_item = Product()
        product_item['url'] = response.url
        product_item['category'] = hxs.select(self.xpath['prod_category']).extract()
        if not self._validate_not_empty('product category', product_item['category'], response):
            return
        prod_content = hxs.select(self.xpath['prod_content'])
        if not self._validate_not_empty('product content', prod_content, response):
            return
        else:
            prod_content = prod_content[0]
        product_item['name'] = prod_content.select(self.xpath['prod_title']).extract()
        if not self._validate_not_empty('product name', product_item['name'], response):
            return
        product_item['image_url'] = prod_content.select(self.xpath['prod_image']).extract()
        if not self._validate_not_empty('product image', product_item['image_url'], response):
            return
        prod_price = prod_content.select(self.xpath['prod_price']).extract()
        if not self._validate_not_empty('product price', prod_price, response):
            return
        prod_price_match = self.re['prod_price'].search(prod_price[0])
        if not self._validate_value('product price', prod_price_match, response):
            return
        product_item['price'] = float(prod_price_match.groups()[0])
        prod_code = prod_content.select(self.xpath['prod_code']).extract()
        if not self._validate_not_empty('product code', prod_code, response):
            return
        yield Request(
            self.xhr_url + prod_code[0].replace('Product Code:','').strip(),
            headers=self.xhr_header,
            callback=self.parse_code,
            meta= {
                'product_item': product_item,
                'prod_content': prod_content,
                'url_id': url_id,
            }
        )

    def parse_code(self, response):
        try:
            json_doc = json.loads(response.body)
            tree = document_fromstring(json_doc['html'])
            prod_codes = tree.xpath('//li/text()')
        except Exception as e:
            self.log('Cannot parse codes %s' % str(e), level=log.ERROR)
            return
        if not self._validate_not_empty('product codes', prod_codes, response):
            return
        product_item = response.meta['product_item']
        prod_content = response.meta['prod_content']
        url_id = response.meta['url_id']
        products = {}
        for code in prod_codes:
            code_data = self.re['prod_code'].search(code)
            if not self._validate_value('code data', code_data, response):
                continue
            code_data = code_data.groupdict()
            products[code_data['option']] = code_data
        if not self._validate_value('products', products, response):
            return
        if len(products) == 1:
            prod = products.values()[0]
            product_item['sku'] = url_id + prod['code'] + (prod['option'] if prod['option'] else '')
            product_item['identifier'] = product_item['sku']
            product_item['stock'] = 1 if int(prod['stock']) else 0
            yield self._load_item(product_item, response)
        else:
            options = prod_content.select(
                './/div[@class="add-product-cart"]//select/option/text()'
            ).extract()
            if not options:
                for prod in products.values():
                    if not prod['option']:
                        continue
                    product = Product(product_item)
                    product['name'] = product['name'][0] + ' ' + prod['option'].strip('/')
                    product['sku'] = url_id + prod['code'] + prod['option']
                    product['identifier'] = product['sku']
                    product['stock'] = 1 if int(prod['stock']) else 0
                    yield self._load_item(product, response)
            else:
                for option in options:
                    option_data = self.re['prod_option'].search(option)
                    if not self._validate_value('product option', option_data, response):
                        continue
                    option_data = option_data.groupdict()
                    if option_data['option'] not in products:
                        prod = products[None]
                    else:
                        prod = products[option_data['option']]
                    overprice = float(option_data['overprice']) if option_data['overprice'] else 0
                    product = Product(product_item)
                    product['name'] = product['name'][0] + ' ' + option_data['option'].strip('/')
                    product['price'] += overprice
                    product['sku'] = url_id + prod['code'] + option_data['option']
                    product['identifier'] = product['sku']
                    product['stock'] = 1 if int(prod['stock']) else 0
                    yield self._load_item(product, response)

    def _load_item(self, product_item, response):
        product_loader = ProductLoader(Product(), response=response)
        for key, val in product_item.iteritems():
            product_loader.add_value(key, val)
        return product_loader.load_item()

    def _extract_price(self, data):
        try:
            return float(data)
        except ValueError:
            return

    def _validate_not_empty(self, key, value, response):
        if not (value and value[0]):
            self.log('No %s :: %s' % (key, response.url), level=log.ERROR)
            return False
        return True

    def _validate_value(self, key, value, response):
        if value != 0 and not value:
            self.log('No %s :: %s' % (key, response.url), level=log.ERROR)
            return False
        return True


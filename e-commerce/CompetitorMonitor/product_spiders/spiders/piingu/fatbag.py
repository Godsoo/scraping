# -*- coding: utf-8 -*-
import re
import json

from scrapy.spider import BaseSpider
from scrapy.http import Request, FormRequest
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu



class FatbagSpider(BaseSpider):
    name = 'piingu-fatbag.dk'
    allowed_domains = ['fatbag.dk']
    start_urls = ('https://fatbag.dk',)
    errors = []

    def parse(self, response):
        url = 'https://fatbag.dk/api/products'
        body = {u'count': 99999, 
                u'forMen': False, 
                u'brandIds': [], 
                u'forWomen': False, 
                u'sortKey': u'0', 
                u'forChildren': False, 
                u'offset': 0, 
                u'subCategoryIds': [], 
                u'categoryIds': []}
        yield Request(url, body=json.dumps(body), headers={'Content-Type':'application/json'}, callback=self.parse_products)

    def parse_products(self, response):
        products_data = json.loads(response.body)
        products = products_data['variants']
        for product in products:
            yield Request(response.urljoin(product['viewUrl']), callback=self.parse_product_data)

    def parse_product_data(self, response):
        url = "https://fatbag.dk/api/product"

        product_url = response.xpath('//span[@model="productUrl"]/@value').extract()[0]
        brand_url = response.xpath('//span[@model="brandUrl"]/@value').extract()[0]
        body = {"productUrl": product_url,
                "brandUrl": brand_url}
        yield Request(url, body=json.dumps(body), headers={'Content-Type':'application/json'}, callback=self.parse_product, meta={'url': response.url})

    def parse_product(self, response):
        product = json.loads(response.body)

        url = response.meta['url']
        category = product['category']
        brand = product['brand']
        name = product['title']
 
        for option_desc, option in product['variants'].iteritems():
            product_loader = ProductLoader(item=Product(), response=response)
            product_loader.add_value('identifier', option['id'])
            product_loader.add_value('sku', option['id'])
            product_loader.add_value('image_url', option['imageUrl'])
            product_loader.add_value('name', name + ' ' + option['title'])
            product_loader.add_value('url', url)
            product_loader.add_value('category', category)
            product_loader.add_value('brand', brand)
            product_loader.add_value('price', option['salesPrice'])
            product_loader.add_value('stock', option['stock'])
            yield product_loader.load_item()

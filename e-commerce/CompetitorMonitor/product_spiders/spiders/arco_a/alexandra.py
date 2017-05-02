import re
import os

from product_spiders.base_spiders.primary_spider import PrimarySpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
import hashlib

import csv
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from scrapy import log
from scrapy.shell import inspect_response

from urlparse import urljoin

import itertools
import json
import copy

HERE = os.path.abspath(os.path.dirname(__file__))

class AlexandraSpider(PrimarySpider):
    name = 'arco-a-alexandra.co.uk'
    allowed_domains = ['alexandra.co.uk']
    start_urls = ['http://www.alexandra.co.uk']
    csv_file = 'alexandra.co.uk_crawl.csv'

    def parse(self, response):
        # inspect_response(response, self)
        # return
        hxs = HtmlXPathSelector(response)
        tmp = hxs.select('//div[@class="header-minicart"]/a[text()="(Show prices ex. VAT)"]/@href').extract()
        if tmp:
            yield Request(tmp[0], dont_filter=True, callback=self.parse_home)
        else:
            log.msg('### Entry of ex. VAT was not found!', level=log.ERROR)

    def parse_home(self, response):
        # inspect_response(response, self)
        # yield Request('http://www.alexandra.co.uk/healthcare/tunics/where/p/2', callback=self.parse_products_list)
        # return
        hxs = HtmlXPathSelector(response)
        for link in hxs.select('//ol[@class="nav-primary"]/li/ul/li/div/ul/li/a/@href').extract():  # ##
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_products_list)

    def parse_products_list(self, response):
        # inspect_response(response, self)
        # return
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[@class="breadcrumbs"]/ul/li[contains(@class,"category")]/*[self::a or self::strong]/text()').extract()
        # Scrape products.
        for url in hxs.select('//ul[contains(@class,"products-grid")]/li//h2[@class="product-name"]/a/@href').extract():  # ##
            # url = urljoin(response.url, link)
            yield Request(url, meta={'categories':categories}, callback=self.parse_product)
        # Crawl next page
        #return ###
        tmp = hxs.select('//div[@class="pages-inner"]//a[@title="Next"]/@href').extract()
        if tmp:
            yield Request(tmp[0], callback=self.parse_products_list)

    def parse_product(self, response):
        # inspect_response(response, self)
        # return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        for s in response.meta.get('categories', []):
            loader.add_value('category', s)
        product = loader.load_item()
        product['url'] = response.url

        tmp = hxs.select('//div[@class="product-sku"]/text()').extract()
        if tmp:
            product['sku'] = tmp[0].replace('Product Code: ', '').strip()

        identifier = hxs.select('//form[@id="product_addtocart_form"]/@action').re(r'/product/(.*)/form_key')
        if identifier:
            product['identifier'] = identifier[0]
        name = ''
        tmp = hxs.select('//div[@class="product-name"]/span/text()').extract()
        if tmp:
            name = tmp[0]
        product['name'] = name
        tmp = hxs.select('//div[@class="price-info"]//span[@itemprop="price"]/text()').extract()
        if tmp:
            price = extract_price(tmp[0])
            product['price'] = price
            if price < 30:
                product['shipping_cost'] = extract_price('4.99')
            else:
                product['shipping_cost'] = extract_price('0')
        tmp = hxs.select('//div[@class="product-image-gallery"]/img[1]/@src').extract()
        if tmp:
            product['image_url'] = tmp[0]
        tmp = hxs.select('//div[@class="product-detail-guides"]//span[@class="value"and text()="In stock"]')
        if tmp:
            product['stock'] = 1
        else:
            product['stock'] = 0
        if not ('new Product.Config(' in response.body and 'new AmConfigurableData(' in response.body):
            log.msg('### Json data not found at ' + response.url, level=log.INFO)
            yield product
        else:
            data = response.body.split('new Product.Config(', 1)[1].split(');\n', 1)[0]
            jconfig = json.loads(data)
            basePrice = float(jconfig.get('basePrice', '0'))
            data = response.body.split('new Redbox.Backorder(', 1)[1].split(');', 1)[0]
            jstock = json.loads(data)

            prices = {}
            if 'new Redbox.PriceMultiplier(' in response.body:
                data = response.body.split('new Redbox.PriceMultiplier(', 1)[1].split(');', 1)[0]
                jprice = json.loads(data)
                for id, opts in jprice['products'].items():
                    for opt in opts:
                        if opt.get('min_qty') == 1:
                            prices[id] = opt.get('price')
            # if not jstock.keys():
            #    yield product
            #    return
            product_data = {}
            for key, value in jstock.get('products').iteritems():
                product_data[key] = {}
                product_data[key]['stock'] = value.get('stock', 0)
                product_data[key]['name'] = []
                product_data[key]['price'] = 0

            for value in jconfig.get('attributes', {}).values():
                for option in value.get('options', {}):
                    for product_id in option.get('products', []):
                        if option.get('price', 0):
                            product_data[product_id]['price'] = product_data[product_id]['price'] + extract_price(option['price'])
                        if 'image_url' in option:
                            product_data[product_id]['image_url'] = option['image']
                        if 'label' in option:
                            product_data[product_id]['name'].append(option['label'])

            for key, value in product_data.iteritems():
                if not value.get('name', False):
                    continue
                item = copy.deepcopy(product)
                item['sku'] = item['identifier']
                item['identifier'] = key
                if key in prices:
                    price = prices[key]
                else:
                    price = basePrice + int(value['price'])
                item['price'] = price
                if 'image_url' in value:
                    item['image_url'] = value['image_url']
                if price < 30:
                    item['shipping_cost'] = extract_price('4.99')
                else:
                    item['shipping_cost'] = extract_price('0')
                item['name'] = name + ' - ' + '-'.join(reversed(value['name']))

                # Scrape image
                # http://www.alexandra.co.uk/amconf/media/index/id/50379/
                # yield Request('http://www.alexandra.co.uk/amconf/media/index/id/%s/' % value['product_id'], meta={'item':item}, callback=self.parse_image)
                yield item
                #break ###

    def parse_image(self, response):
        # inspect_response(response, self)
        # return
        hxs = HtmlXPathSelector(response)
        item = response.meta['item']
        tmp = hxs.select('//img[@id="image-main"]/@src').extract()
        if tmp:
            item['image_url'] = tmp[0]
        return item


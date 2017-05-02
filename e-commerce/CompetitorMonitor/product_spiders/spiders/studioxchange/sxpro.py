import re
import os

from scrapy.spider import BaseSpider
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

class SxproSpider(BaseSpider):
    name = 'studioxchange-sxpro.co.uk'
    allowed_domains = ['sxpro.co.uk']
    start_urls = ['http://sxpro.co.uk/brands']
    #start_urls = ['http://sxpro.co.uk']
    brands = []
    extra_categories = ['http://sxpro.co.uk/guitar-amplifiers', 
                        'http://sxpro.co.uk/guitar-fx', 
                        'http://sxpro.co.uk/keyboards-synths', 
                        'http://sxpro.co.uk/live-sound', 
                        'http://sxpro.co.uk/recorders']

    def parse(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)
        self.brands = hxs.select('//div[preceding-sibling::h1="All Brands"]//a/text()').extract()
        for url in response.xpath('//div[preceding-sibling::h1="All Brands"]//a/@href').extract():
            yield Request(response.urljoin(url), callback=self.parse_products_list)
        yield Request('http://sxpro.co.uk', callback=self.parse_home)

    def parse_home(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//ul[@id="menu"]//a/@href').extract()[:-1]
        categories += self.extra_categories

        for link in categories: ###
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        for url in response.css('.ProductList').xpath('./li/div[1]/a/@href').extract(): ###
            yield Request(url, callback=self.parse_product)

        #To crawl next page.
        tmp = hxs.select('//div[@class="CategoryPagination"]//a[contains(text(),"Next")]/@href').extract()
        if tmp:
            yield Request(tmp[0], callback=self.parse_products_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        tmp = hxs.select('//form[@id="productDetailsAddToCartForm"]/input[@name="product_id"]/@value').extract()
        if tmp:
            loader.add_value('identifier', tmp[0])
        else:
            log.msg('### No product ID at '+response.url, level=log.INFO)

        sku = re.search('Product SKU: (.*?) -->', ' '.join(response.body.split()))

        sku = sku.group(1) if sku else ''
        loader.add_value('sku', sku)

        name = hxs.select('//div[@id="ProductDetails"]/div/h1/text()').extract()
        if name:
            loader.add_value('name', name[0].strip())
        else:
            log.msg('### No name at '+response.url, level=log.INFO)
        #price
        price = hxs.select('//span[@class="ProductDetailsPriceIncTax"]/text()').extract()
        if price:
            price = extract_price(price[0].split()[0])
            loader.add_value('price', price)
        else:
            return
        #image_url
        image_url = hxs.select('//div[@class="ProductThumbImage"]//img[1]/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])
        #get brand
        for brand in self.brands:
            #if brand in name:
            if name and name[0].startswith(brand):
                loader.add_value('brand', brand)
                break
        #category
        tmp = hxs.select('//div[@id="ProductBreadcrumb"]/ul/li/a/text()').extract()
        if len(tmp)>1:
            loader.add_value('category', tmp[1])
        #shipping_cost

        #stock
        tmp = hxs.select('//div[@class="ProductPriceWrap"]//em[text()="Call for pricing"]')
        if tmp:
            loader.add_value('stock', 0)
        else:
            loader.add_value('stock', 1)

        #process options
        product = loader.load_item()

        yield product

    def get_options(self, response):
        hxs = HtmlXPathSelector(response)
        options = []
        options_containers =  hxs.select('//div[@class="productAttributeList"]/div/div[@class="productAttributeValue"]/div/select')

        combined_options = []
        for options_container in options_containers:
            element_options = []
            key = options_container.select('@name').extract()[0]
            for option in options_container.select('option')[1:]:
                option_id = option.select('@value').extract()[0]
                option_desc = option.select('text()').extract()[0]
                option_attr = {key:option_id}
                element_options.append((option_id, option_desc, option_attr))
            combined_options.append(element_options)

        combined_options =  list(itertools.product(*combined_options))
        for combined_option in combined_options:
            name, option_id, option_attr = '', '', {}
            for option in combined_option:
                option_id = option_id + '-' + option[0]
                name = name + ' - ' + option[1]
                option_attr.update(option[2])
            options.append((option_id, name, option_attr))
        return options

    def parse_option(self, response):
        item = response.meta['item']
        j = json.loads(response.body)
        try:
            price = extract_price(str(round(float(j['details']['unformattedPrice'])*1.2, 2)))
        except KeyError:
            return
        item['price'] = price
        return item


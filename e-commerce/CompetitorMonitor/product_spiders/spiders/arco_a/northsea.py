import re
import os

# from scrapy.spider import BaseSpider
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

import itertools

HERE = os.path.abspath(os.path.dirname(__file__))

class NorthseaSpider(PrimarySpider):
    name = 'arco-a-northseaworkwear.com'
    allowed_domains = ['northseaworkwear.com']
    start_urls = [
        'https://www.northseaworkwear.com/',
#        'https://www.northseaworkwear.com/changetaxtype/0?returnurl=%2f',
        ]
    brands = []
    cookie_num = 0

    csv_file = 'northseaworkwear_crawl.csv'

    def parse(self, response):
        # inspect_response(response, self)
        # yield Request('http://www.northseaworkwear.com/wenaas-2-tone-hi-vis-coverall-300g-redyellow-non-fr', meta={'category':'test'}, callback=self.parse_product)
        # return
        hxs = HtmlXPathSelector(response)
        self.brands = hxs.select('//ul[@class="mega-menu"]/li[a="Brands"]/div//a/strong/text()').extract()
        cls = [' FR Workwear & Boots', ' Eye & Workwear', ' Shoes & Boots',
                ' Boots & Shoes',
                ' PPE', ' Solutions', ' Footwear', ' Gloves', ' Workwear',
            ' Eyewear', ' Clothing', ' Safety',
            ' Undergarments', ' Earplugs', ' Rainwear',
            ' Flotation', ' Helmets', ' Diving Equipment', ' FR Coveralls',
            ' Chainsaw Protection', ' Boots', ' Wellingtons']
        for i in range(len(self.brands)):
            s = self.brands[i]
            for c in cls:
                s = s.replace(c, '')
            self.brands[i] = s
        # print '### Brands:', self.brands
        for link in hxs.select('//ul[@class="mega-menu"]/li[a="Products"]/div//strong/a/@href').extract():  # ##
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_products_list)

    def parse_products_list(self, response):
        # inspect_response(response, self)
        # return
        hxs = HtmlXPathSelector(response)
        links = hxs.select('//div[@class="sub-category-grid"]//h2/a/@href').extract()
        if links:
            # sub-categories page
            for link in links:  # ##
                url = urljoin(response.url, link)
                yield Request(url, callback=self.parse_products_list)
            return

        # Products list page
        # inspect_response(response, self)
        # return
        category = ''.join(hxs.select('//ul[@class="list"]//li[@class="active"]/a/text()').extract()).strip()
        category = ' '.join(category.split())

        for link in hxs.select('//div[@class="product-grid"]//h2/a/@href').extract():  # ##
            url = urljoin(response.url, link)
            yield Request(url, meta={'category':category}, callback=self.parse_product)

        # Crawl next page
        #return ###
        tmp = hxs.select('//div[@class="pager"]/ul/li/a[text()="Next"]/@href').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            yield Request(url, callback=self.parse_products_list)

    def parse_product(self, response):
        # inspect_response(response, self)
        # return
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
	
	if not hxs.select('//select[@id="customerTaxType"]/option[@selected="selected"]').re('Excl'):
	  url = hxs.select('//select[@id="customerTaxType"]/option[not (@selected)]/@value').extract()
	  yield Request(urljoin(base_url, url[0]), callback=self.parse_product, dont_filter=True, meta=response.meta)
	  return
	
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        loader.add_value('category', response.meta['category'])
        name = ''
        tmp = hxs.select('//h1[@itemprop="name"]/text()').extract()
        if tmp:
            name = tmp[0].strip()
            loader.add_value('name', name)
        tmp = hxs.select('//div[@class="gallery"]//a[1]/@href').extract()
        if tmp:
            loader.add_value('image_url', tmp[0])
        # Find brand.
        for brand in self.brands:
            if brand.lower() in name.lower():
                loader.add_value('brand', brand)
                break
        # p = loader.load_item()
        tmp = hxs.select('//input[contains(@id,"add-to-cart-button-")]/@data-productid').extract()
        if tmp:
            # identifier = product['identifier']
            loader.add_value('identifier', tmp[0])
        tmp = hxs.select('//p/span[strong="Product Code:"]/text()').extract()
        if tmp:
            loader.add_value('sku', tmp[0].strip())
        tmp = hxs.select('//span[@itemprop="price"]/text()').extract()
        if tmp:
            price = extract_price(tmp[0].strip().split()[0])
            loader.add_value('price', price)

        product = loader.load_item()
        url_post = 'http://www.northseaworkwear.com/addproducttocart/details/%s/1' % product['identifier']
        qty = '1'
        tmp = hxs.select('//input[contains(@class,"qty-input")]/@value').extract()
        if tmp:
            qty = tmp[0]

        selections = hxs.select('//div[@class="attributes"]//select')
        if not selections:
            # loader.add_value('stock', 0)
            # yield loader.load_item()
            formdata = {'addtocart_%s.EnteredQuantity' % product['identifier']:qty}
            self.cookie_num += 1
            yield FormRequest(url_post, formdata=formdata, meta={'item':product, 'cookiejar':self.cookie_num}, dont_filter=True, callback=self.parse_stock)
            return

        attrs = []
        for sel in selections:
            attr_name = ''
            tmp = sel.select('@name').extract()
            if tmp:
                attr_name = tmp[0]
            attr_values = []
            for option in sel.select('option'):
                value = ''
                tmp = option.select('@value').extract()
                if tmp:
                    value = tmp[0]
                txt = ''
                tmp = option.select('text()').extract()
                if tmp:
                    txt = tmp[0].strip()
                if value != '' and value != '0':
                    attr_values.append((attr_name, value, txt))
            attrs.append(attr_values)
        # print '### Selections:', attrs
        for option in itertools.product(*attrs):
            # print '### option:', o
            item = copy.deepcopy(product)
            item['name'] += ' - ' + '-'.join([attr[2] for attr in option])
            item['identifier'] += '-' + '-'.join([attr[1] for attr in option])
            # yield item
            formdata = {'addtocart_%s.EnteredQuantity' % product['identifier']:qty}
            for attr in option:
                formdata[attr[0]] = attr[1]
            # print 'formdata:', formdata
            self.cookie_num += 1
            yield FormRequest(url_post, formdata=formdata, meta={'item':item, 'cookiejar':self.cookie_num}, dont_filter=True, callback=self.parse_stock)
            #break ###

    # POST http://www.northseaworkwear.com/addproducttocart/details/1209/1
    # Form Data
    # product_attribute_1209_1_1446:7676
    # addtocart_1209.EnteredQuantity:1
    # {"success":true,...}
    # j['message']
    # 'The product has been added to your <a href="/cart">shopping cart</a>'
    def parse_stock(self, response):
        # inspect_response(response, self)
        # return
        item = response.meta['item']
        item['name'] = re.sub(r'\s+', ' ', item['name'])
        for add in re.findall(r'\[\+.([\d.,]+)\]', item['name']):
            add = add.replace(',', '')
            item['price'] = extract_price(str(float(item['price']) + float(add)))

        if 'errorpage.htm' in response.url:
            item['stock'] = 1
            return item

        j = json.loads(response.body)
        if j['success']:
            item['stock'] = 1
        else:
            item['stock'] = 0
        if type(j['message']) == str and 'out of stock' in j['message'].lower():
            item['stock'] = 0
        return item



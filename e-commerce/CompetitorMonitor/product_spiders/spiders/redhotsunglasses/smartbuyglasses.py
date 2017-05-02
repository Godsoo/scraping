# -*- coding: utf-8 -*-
"""
Account: Red Hot Sunglasses
Name: tredhotsunglasses-smartbuyglasses.co.uk
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4916

"""

import urlparse
import os
import json
import re

from copy import deepcopy

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))


class SmartBuyGlassesSpider(BaseSpider):
    name = 'redhotsunglasses-smartbuyglasses.co.uk'
    allowed_domains = ['smartbuyglasses.co.uk']
    start_urls = ['http://www.smartbuyglasses.co.uk/']


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        # categories and subcategories
        categories = response.xpath('//ul[@class="nav_menuN"]//a[@href!="#"]/@href').extract()
        for cat_href in categories:
            yield Request(urlparse.urljoin(get_base_url(response), cat_href))

        # products
        products = response.xpath('//div[contains(@class, "proCell")]/ul/a[@href!="#"]/@href').extract()
        for url in products:
            yield Request(url, callback=self.parse_product)

        next = response.xpath('//a[img[contains(@src, "arrow_right")]]/@href').extract()
        if not next:
            next = response.xpath('//a[i[contains(@class, "right")]]/@href').extract()

        if next:
            yield Request(next[0])

        brand_type = re.findall('brandType:"(.*)"', response.body)
        subcategory = re.findall('subCategory:"(.*)"', response.body)
        category = re.findall('categoryString:"(.*)"', response.body)
        current_page = response.xpath('//input[@id="current-page"]/@value').extract()
        if brand_type and current_page:
            formdata = {'brand_type': brand_type[0],
                        'category': category[0],
                        'p': current_page[0],
                        'subcategory': subcategory[0],
                        's': '0',
                        'tb': '0'}
            url = 'http://www.smartbuyglasses.co.uk/contact-lens/auto-filter-search'
            yield FormRequest(url, formdata=formdata, callback=self.parse_contact_lens, meta={'formdata': formdata})

        identifier = re.findall("prodId:\['(.*)'\]", response.body)
        if identifier:
            for item in self.parse_product(response):
                yield item

    def parse_contact_lens(self, response):
        data = json.loads(response.body)

        products = []
        
        for product_data in data['data']:
            if isinstance(product_data, list):
                 for product in product_data:
                     products.append(product)
            else:
                for id, product in product_data.iteritems():
                     products.append(product)

        for product in products:
            yield Request(product['webUrl'], callback=self.parse_product)

        formdata = response.meta['formdata']
        if int(formdata['p']) < data['pageCount']:
            url = 'http://www.smartbuyglasses.co.uk/contact-lens/auto-filter-search'
            formdata['p'] = str(int(formdata['p']) + 1)
            yield FormRequest(url, formdata=formdata, callback=self.parse_contact_lens, 
                              meta={'formdata': formdata})
        

    def parse_product(self, response):
	url = response.url
 
        products = response.xpath('//li[@class="similar_content_element"]/a/@href').extract()
        for product in products:
            yield Request(product, callback=self.parse_product)

        l = ProductLoader(item=Product(), response=response)

        try:
            name = response.xpath('//h1/text()').extract()[0].strip()
        except IndexError:
            retry = response.meta.get('retry', 0)
            if retry <= 3:
                yield Request(response.url, dont_filter=True, callback=self.parse_product, meta={'retry': retry + 1})
            else:
                log.msg('ERROR >>> Product without name: ' + response.url)
            return

        l.add_value('name', name)


        price = response.xpath('//span[@itemprop="price"]/text()').extract()
        
        price = extract_price(price[0]) if price else '0'
        l.add_value('price', price)

        identifier = re.findall("prodId:\['(.*)'\]", response.body)[0]
        l.add_value('identifier', identifier)
        sku = response.xpath('//span[@itemprop="gtin13"]/text()').extract()
        sku = sku[0].strip() if sku else ''
        l.add_value('sku', sku)
        brand = re.findall("pbrand:\['(.*)'\]", response.body)[0]
        l.add_value('brand', brand)
        categories = response.xpath('//div[@class="navigation"]//a/h2/text()').extract()
        if not categories:
            categories = response.xpath('//div[@class="local"]//a/text()').extract()[1:]
        l.add_value('category', categories)

        image_url = response.xpath('//img[@id="big_image"]/@src').extract()
        if not image_url:
            image_url = response.xpath('//img[@id="fancybox-cl-img"]/@src').extract()
        if not image_url:
            image_url = response.xpath('//img[@id="view_image_1"]/@src').extract()

        if image_url:
            l.add_value('image_url', urlparse.urljoin(get_base_url(response), image_url[0]))

        l.add_value('url', url)

        if l.get_output_value('price')<45:
            l.add_value('shipping_cost', 2.99)


        item = l.load_item()

        size_options = response.xpath('//div[@class="pro_right_size"]//a')
        if size_options:
            upc_url = "http://www.smartbuyglasses.co.uk/product/get-upc-by-size/size_id/%s"
            color_id = response.xpath('//input[@id="color_code_id"]/@value').extract()[0]
            brand_id = response.xpath('//input[@name="brand_id"]/@value').extract()[0]
            for size_option in size_options:
                option_item = deepcopy(item)
                size_id = size_option.xpath('@data-size-id').extract()[0]
                size = size_option.xpath('text()').extract()[0]
                option_item['name'] += ' ' + size
                option_item['identifier'] += '-' + size_id
                meta={'item': option_item,
                      'size_id': size_id,
                      'color_id': color_id,
                      'brand_id': brand_id}
                yield Request(upc_url % (size_id), callback=self.parse_upc, meta=meta)
        else:
            yield item

    def parse_upc(self, response):
        data = json.loads(response.body)

        item = response.meta['item']
        color_id = response.meta['color_id']
        brand_id = response.meta['brand_id']
        size_id = response.meta['size_id']

        upc = data['upc']
        if upc:
            item['sku'] = upc['upc']

        size_url = "http://www.smartbuyglasses.co.uk/product/change-new-size-contant/size_id/%s/color_code_id/%s/brand_id/%s"
        yield Request(size_url % (size_id, color_id, brand_id), callback=self.parse_size, meta={'item': item})

    def parse_size(self, response):
        item = response.meta['item']

        data = json.loads(response.body)
        item['price'] = extract_price(data['discount_price_promotion_display'])
        yield item
        if data['with_lens_price']:
            item['price'] = extract_price(data['with_lens_price'])
            item['identifier'] += '-with_lens'
            item['name'] += ' with lenses'
            yield item

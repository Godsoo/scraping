# -*- coding: utf-8 -*-
"""
Customer: Blivakker
Website: https://www.douglas.no/
Extract all products on site including product options. http://screencast.com/t/74r19CqKO5

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4790

"""

import os
import re 
import json
from copy import deepcopy

from scrapy.spider import BaseSpider
from scrapy.http import Request
from product_spiders.utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


from scrapy.selector import XmlXPathSelector

from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter


class DouglasSpider(BaseSpider):
    name = 'blivakker-douglas.no'
    allowed_domains = ['douglas.no']
    #start_urls = ['https://www.douglas.no/douglas/brands-sitemap.xml']
    start_urls = ['https://www.douglas.no/douglas/sitemap.xml']
    product_ids = []

    def parse(self, response):

        xxs = XmlXPathSelector(response)
        xxs.remove_namespaces()
        urls = xxs.select('//loc/text()').extract()
        for url in urls:
            if 'brands-sitemap.xml' in url:
                continue

            if 'productbrand' in url:
                prod_id = re.findall('productbrand_(\d+).html', url)
                prod_id = prod_id[0] if prod_id else ''
                if prod_id:
                    if prod_id in self.product_ids:
                        continue
                    else:
                        self.product_ids.append(prod_id)
                yield Request(url, callback=self.parse_product, meta={"dont_merge_cookies": True})
            else:
                yield Request(url, meta={"dont_merge_cookies": True})

        '''
        categories = response.xpath('//div[@id="mainnav2014"]/ul/li/a/@href').extract()
        #categories += response.xpath('//div[@class="submenu"]//a/@href').extract()
        for category in categories:
            category = response.urljoin(category)
            category = add_or_replace_parameter(category, "sourceRef", "")
            yield Request(category)
        '''

    def parse_products(self, response):
        self.log(response.body)
        products = response.xpath('//div[@class="prodboxinner"]//a[@data-wt-content="link"]/@href').extract()
        for product in products:
            product = response.urljoin(product)

            prod_id = re.findall('productbrand_(\d+).html', product)
            if not prod_id:
                prod_id = re.findall('product_(\d+).html', product)
            prod_id = prod_id[0] if prod_id else ''
            if prod_id:
                if prod_id in self.product_ids:
                    continue
                else:
                    self.product_ids.append(prod_id)

            yield Request(product, callback=self.parse_product, meta={"dont_merge_cookies": True})

        next = response.xpath('//a[@class="page next"]/@href').extract()
        if next:
            next = response.urljoin(next[0])
            yield Request(next, callback=self.parse_products, meta={"dont_merge_cookies": True})

    def parse_product(self, response):

        variants = response.xpath('//a[contains(@id, "smallVariant")]/@href').extract()
        for variant in variants:
            variant = response.urljoin(variant)

            prod_id = re.findall('productbrand_(\d+).html', variant)
            if not prod_id:
                prod_id = re.findall('product_(\d+).html', variant)
            prod_id = prod_id[0] if prod_id else ''
            if prod_id:
                if prod_id in self.product_ids:
                    continue
                else:
                    self.product_ids.append(prod_id)
            yield Request(variant, callback=self.parse_product, meta={"dont_merge_cookies": True})

        loader = ProductLoader(item=Product(), response=response)
        sku = response.xpath('//div[@class="variantBox active"]//span[@class="articleno"]/text()').re('(\d+)')[0]

        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)

        name = response.xpath('//span[@itemprop="name"]/text()').extract()[0].strip()
        desc = response.xpath('//p[@class="productname"]/text()').extract()
        if desc:
            name += ' ' + desc[0].strip()

        variant_name = response.xpath('//div[@class="variantBox active"]//span[contains(@class, "variantLabel")]/text()').extract()
        if variant_name:
           variant_name = ' '.join(variant_name[0].split())
           if variant_name.upper() not in name.upper().strip():
               name += ' ' + variant_name

        option_name = response.xpath('//div[@class="variantBox active"]//strong[@class="artikelname"]/text()').extract()
        if option_name:
            name += ' ' + option_name[0]
        loader.add_value('name', name)

        loader.add_value('url', response.url)

        brand = response.xpath('//img[@class="productbrand"]/@alt').extract()
        brand = brand[0] if brand else ''
        loader.add_value('brand', brand)

        price = response.xpath('//div[@class="variantBox active"]//p[@class="price sale"]/strong/text()').extract()
        if not price:
            price = response.xpath('//div[@class="variantBox active"]//p[@class="price"]/text()').extract()
        price = ''.join(price[0].split())
        loader.add_value('price', extract_price(price))

        image_url = response.xpath('//div[@class="bigimage"]/a/@href').extract()
        image_url = response.urljoin(image_url[0]) if image_url else ''
        loader.add_value('image_url', image_url)

        categories = response.xpath('//div[@id="breadcrumbs"]/span/a/span/text()').extract()[1:]
        loader.add_value('category', categories)

        out_of_stock = response.xpath('//div[@class="variantBox active"]//div[contains(@class, "available-soon")]/text()').extract()
        if out_of_stock:
            loader.add_value('stock', 0)

        if loader.get_output_value('price') < 600:
            loader.add_value('shipping_cost', 45)
        else:
            loader.add_value('shipping_cost', 0)

        item = loader.load_item()
 
        yield item



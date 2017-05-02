# -*- coding: utf-8 -*-

import csv
import os
import re
import json

from decimal import Decimal
from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.fuzzywuzzy import process
from product_spiders.fuzzywuzzy import fuzz

HERE = os.path.abspath(os.path.dirname(__file__))

class WearepetsSpider(BaseSpider):
    name = 'wearepets.co.uk'
    allowed_domains = ['wearepets.co.uk']
    start_urls = [
        #'http://www.wearepets.co.uk/sitemap'
        'http://wearepets.co.uk/catalog/seo_sitemap/category/'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        #categories = hxs.select('//*[@id="ThreeColMiddle"]/ul/li/a/@href ').extract()
        categories = hxs.select('//ul[@class="sitemap"]/li/a/@href').extract()

        for category in categories:
            url =  urljoin_rfc(get_base_url(response), category)
            yield Request(url, callback=self.parse_products)

    def parse_products(self, response):

        hxs = HtmlXPathSelector(response)

        #products = hxs.select('//li[@class="item" or @class="item lastItem"]')
        products = hxs.select('//div[contains(@class,"product-row")]/div[contains(@class,"itemProduct")]')

        for product in products:

            #name = product.select('div/h3/a/span/text()').extract()[0]

            name = product.select(".//div[@class='descripProd']/span/a/text()").extract()
            if not name:
                self.log("ERROR name not found")
                continue
            else:
                name = name[0].strip()

            #url = product.select('div/h3/a/@href').extract()
            url = product.select(".//div[@class='productImage']/a/@href").extract()[0]
            if not url:
                self.log("ERROR url not found")
                continue

            yield Request(url, callback=self.parse_options, meta={'name':name})



        next = hxs.select('//div[@class="listing-pager"]//a[contains(text(),"Next")]/@href').extract()

        if next:
            url =  urljoin_rfc(get_base_url(response), next[0])
            yield Request(url, callback=self.parse_products)


    def parse_options(self, response):
        hxs = HtmlXPathSelector(response)

        image_url = hxs.select('//div[@class="product-media"]/a[contains(@class,"product-image") and contains(@class,"primary")]/img/@src').extract()
        if not image_url:
            self.log("ERROR image not found")

        category =  hxs.select('(//ul[@class="breadcrumbs"]//li[contains(@class,"category")])[last()]/a/text()').extract()
        if not category:
            self.log("ERROR category not found")

        brand = hxs.select('//*[@id="product-attribute-specs-table"]//tr[.//th[contains(text(),"Brand")]]/td/text()').extract()
        if not brand:
            self.log("ERROR brand not found")

        base_price = hxs.select('//span[@class="price" and (contains(@id,"product-price") or contains(parent::span/@id,"product-price"))]/text()').extract()
        if not base_price:
            self.log("ERROR base_price not found")
            base_price = "0"
        else:
            base_price = base_price[0].strip()

        base_identifier = hxs.select('//input[@name="product"]/@value').extract()
        if not base_identifier:
            self.log("ERROR base_identifier not found")

        options = []
        options_script = re.findall("spConfig = new Product\.Config.*;",response.body)
        if options_script:

            m = re.search('(\"options.*?}\])', options_script[0])
            if m:
                options_json = "{" +m.group(1) + "}"

                body_dict = json.loads(options_json)

                options = [[option['price'], option['label'], option['products'][0]] for option in body_dict['options']]

        if options:
            for option in options:

                #self.log("option name: " + option[1] + ", price: " + option[0])

                loader = ProductLoader(item=Product(), response=response)

                loader.add_value('name', ' '.join((response.meta['name'], option[1])))
                loader.add_value('url', response.url)

                if image_url:
                    loader.add_value('image_url', image_url[0])
                if category:
                    loader.add_value('category', category[0])
                if brand:
                    loader.add_value('brand', brand[0])

                if base_price:
                    loader.add_value('price', base_price)


                option_identifier = option[2]
                if not option_identifier:
                    self.log("ERROR option_identifier not found")
                    continue
                loader.add_value('identifier',option_identifier)

                product = loader.load_item()

                #add option price
                if not 'price' in product:
                    product['price'] = Decimal(0)
                    self.log('ERROR price is not set, setting to default 0')
                else:
                    product['price'] = product['price'] + Decimal(option[0])




                yield product
        else:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', response.meta['name'])
            loader.add_value('url', response.url)

            if base_price:
                loader.add_value('price', base_price)
            if image_url:
                loader.add_value('image_url', image_url[0])
            if category:
                loader.add_value('category', category[0])
            if brand:
                loader.add_value('brand', brand[0])
            if base_identifier:
                loader.add_value('identifier',base_identifier[0])

            yield loader.load_item()
          

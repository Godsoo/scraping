from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from product_spiders.phantomjs import PhantomJS

from scrapy import log

import re
import json

class HealsSpider(BaseSpider):
    name = 'made-heals'
    allowed_domains = ['heals.co.uk', 'healssofas.co.uk', 'heals.com']
    start_urls = ['http://www.heals.com',]

    def try_create_browser(self, tries=5):
        for i in range(tries):
            try:
                browser = PhantomJS.create_browser()
                return browser
            except:
                pass

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//nav[@id="nav"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_cat)

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)

        #browser = self.try_create_browser()
        #if not browser:
            #self.log("Error: can't create browser")
        #browser.get(response.url + '#esp_viewall=y')

        #hxs = HtmlXPathSelector(text=browser.page_source)

        products = hxs.select('//form//h2//a/@href').extract()
        products += hxs.select('//h2//a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product)

        for next_page in hxs.select('//div[@class="pages"]//li/a/@href').extract():
            yield Request(next_page, callback=self.parse_cat)
            
        #next = hxs.select('//span[@class="pagnNext"]/a/@data-page').extract()
        #while next:
            #next_url = response.url.split('#')[0]+'#esp_viewall=y&esp_pg='+next[0]
            #browser.get(next_url)
            #hxs = HtmlXPathSelector(text=browser.page_source)

            #for url in hxs.select('//form//h2//a/@href').extract():
                #yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product)

            #next = hxs.select('//span[@class="pagnNext"]/a/@data-page').extract()

#        browser.quit()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

 
        option_links = hxs.select('//div[@class="title"]/h2/a[@class="availlink"]/@href').extract()
        option_links += hxs.select('//ol[@class="mini-products-list products-list"]//p[@class="product-name"]/a/@href').extract()
        if option_links:
            for option_link in option_links:
                yield Request(option_link, callback=self.parse_product)
            return 

        options_config = hxs.select('//script/text()').re('Product.Config\((.*"productAttributes")')

        if options_config:
            options_config = options_config[0] + ':""}'
            product_data = json.loads(options_config)
            products = {}
            prices = {}
            options_ids = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))
                        options_ids[product] = option['id']

            for option_identifier, option_name in products.iteritems():
                loader = ProductLoader(item=Product(), selector=hxs)

                loader.add_value('identifier', option_identifier)
                loader.add_value('sku', product_data['productId'])
                loader.add_value('url', response.url)
                loader.add_value('name', product_data['productName'] + products[option_identifier])
                loader.add_value('price', product_data['childProducts'][option_identifier]['price'])
                if loader.get_output_value('price') < 50.0:
                    loader.add_value('shipping_cost', '5.95')
                loader.add_xpath('image_url', '//img[@itemprop="image"]/@src')
                categories = hxs.select('//div[@class="breadcrumbs"]//a/text()').extract()
                for category in categories:
                    if category.upper() not in ('HOME', 'SHOP', 'CATEGORIES'):
                        loader.add_value('category', category)

                loader.add_xpath('brand', '//div[@class="product-name"]/p[@class="brand"]/a/text()')
                if loader.get_output_value('price'):
                    loader.add_value('stock', '1')
                else:
                    loader.add_value('stock', '0')

                yield loader.load_item()
            
        else:

            loader = ProductLoader(item=Product(), selector=hxs)

            price = hxs.select('//div[@class="price-box"]//span[@class="price"]/text()').extract()[0]
            try:
                identifier = hxs.select('//input[@name="product"]/@value').extract()[0]
            except IndexError:
                yield Request(response.url, callback=self.parse_cat)
                return
            loader.add_value('identifier', identifier)
            loader.add_value('sku', identifier)
            loader.add_value('url', response.url)
            loader.add_xpath('name', '//h1[@itemprop="name"]//text()')
            loader.add_value('price', price)
            if loader.get_output_value('price') < 50.0:
                loader.add_value('shipping_cost', '5.95')
            loader.add_xpath('image_url', '//img[@itemprop="image"]/@src')
            categories = hxs.select('//div[@class="breadcrumbs"]//a/text()').extract()
            for category in categories:
                if category.upper() not in ('HOME', 'SHOP', 'CATEGORIES'):
                    loader.add_value('category', category)

            loader.add_xpath('brand', '//div[@class="product-name"]/p[@class="brand"]/a/text()')
            if loader.get_output_value('price'):
                loader.add_value('stock', '1')
            else:
                loader.add_value('stock', '0')

            yield loader.load_item()

# -*- coding: utf-8 -*-

from copy import deepcopy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request, FormRequest
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from decimal import Decimal
from product_spiders.utils import fix_spaces, extract_price
import re, json, itertools
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class SleepingSolutions(BaseSpider):
    name = "colourbank-sleepingsolutions.co.uk"
    allowed_domains = ["sleepingsolutions.co.uk"]
    start_urls = ["http://www.sleepingsolutions.co.uk"]


    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        category_urls = hxs.select('//div[@id="lnav"]//a/@href').extract()
        for url in category_urls:
            yield Request(urljoin(base_url, url))
            
        next_page_url = hxs.select('//span[@class="next"]/a/@href').extract()
        if next_page_url:
            yield Request(urljoin(base_url, next_page_url[0]))

        #subcategory_urls = hxs.select('//table[@class="ckm-catchild"]/tr/td/a/@href').extract()
        #for url in subcategory_urls:
        #    yield Request(urljoin(base_url, url), callback=self.parse_category)

        product_urls = hxs.select('//div[contains(@class, "product-info")]/h2/a/@href').extract()
        for url in product_urls:
            yield Request(urljoin(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        size_options = hxs.select('//ul[@id="sizenav"]/li/a/@href').extract()
        for size_option in size_options:
            yield Request(urljoin(base_url, size_option), callback=self.parse_product)

        name = hxs.select('//div[@id="ckm-flytitle"]/text()').extract()
        if not name:
            name = hxs.select('//h1[@class="gap"]/text()').extract()

        name = name[0].strip()

        image_url = hxs.select('//div[@class="product-image"]/img/@src').extract()
        image_url = urljoin(base_url, image_url[0]) if image_url else ''

        categories = hxs.select('//div[@id="trail"]/a/text()').extract()
        categories = categories[1:-1] if categories else ''

        column_names = hxs.select('//div[@id="products"]/table//tr/td[@class="title"]//text()').extract()

        products = hxs.select('//div[@id="products"][1]/table//tr[td/input]')
        for product in products:
            loader = ProductLoader(selector=hxs, item=Product())
            name = ''.join(product.select('td[1]/text()').extract()).strip()
            loader.add_value('name', name)

            try:
                price_index = str(column_names.index(u'Our price') + 1)
            except:
                price_index = None

            if price_index:
                price = product.select('td['+price_index+']/text()').extract()
                if not price:
                    price = product.select('td['+price_index+']/span/text()').extract()
                price = price[0]
            else:
                price = 0

            loader.add_value('price', extract_price(price))
            identifier = product.select('td/input[@name="productid"]/@value').extract()
            if not identifier:
                identifier = product.select('preceding-sibling::input[@name="productid"]/@value').extract()
            if not identifier:
                log.msg('ERROR >>> Product without identifier: ' + response.url)
                return
            loader.add_value('identifier', identifier[0])
            loader.add_value('sku', identifier[0])
            loader.add_value('image_url', image_url)
            loader.add_value('category', categories)
            loader.add_value('url', response.url)
            item = loader.load_item()


            try:
                colour_index = column_names.index(u'Colour\xa0')
            except:
                try:
                    colour_index = column_names.index(u'Base Colour\xa0')
                except:
                    colour_index = None

            if colour_index:
                colour_index = str(colour_index + 1)
                colour_options = product.select('td['+colour_index+']/select/option')
                for option in colour_options:
                    option_product = deepcopy(item)
                    option_identifier = option.select('@value').extract()[0]
                    option_name = option.select('text()').extract()[0]
                    option_product['identifier'] = option_product['identifier'] + '-' + option_identifier
                    option_product['name'] = option_product['name'] + '-' + option_name
                    option_product['sku'] = option_product['identifier']
                    yield option_product
            else:
                yield item


        

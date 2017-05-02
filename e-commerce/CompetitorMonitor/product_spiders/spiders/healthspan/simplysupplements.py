import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
import hashlib

import csv

from product_spiders.items import Product, ProductLoaderWithNameStrip\
                             as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))


class SimplySupplementsSpider(BaseSpider):
    name = 'healthspan-simplysupplements.net'
    allowed_domains = ['simplysupplements.net']
    start_urls = ('http://www.simplysupplements.net',)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return

        categories = response.xpath('//ul[@class="topmenu"]//a/@href').extract()
        for category in categories:
            url = response.urljoin(category)
            yield Request(url)

        products = response.xpath('//h2/a/@href').extract()
        for product in products:
            url = response.urljoin(product)
            category = response.xpath('//div[@class="cat-overlay"]/h1/text()').extract()
            if not category:
                category = response.xpath('//div[@class="innercol"]/h1/text()').extract()
            category = category[0]
            yield Request(url, callback=self.parse_product, meta={'category': category})

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        name = response.xpath('//*[@itemprop="name"]/text()').extract()
        if name:
            name = name[0].strip()
            main_id = response.xpath('//input[@name="product"]/@value').extract()[0]
            url = response.url
            price = re.findall("ecomm_totalvalue: '(.*)',", response.body)
            if not price or price and not price[0]:
                price = response.xpath('//div[@class="pricemessage"]/div/text()').extract()
            price = price[0] if price else 0
            image_url = response.xpath('//div[@id="product_top_section"]//img[@itemprop="image"]/@src').extract()
            if not image_url:
                image_url = response.xpath('//span[@class="image-missing"]/img/@src').extract()
            image_url = response.urljoin(image_url[0]) if image_url else ''
            brand = re.findall("'brand': '(.*)',", response.body)
            brand = brand[0] if brand else ''

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('url', url)
            loader.add_value('name', name)
            loader.add_value('price', price)
            loader.add_value('brand', brand)
            loader.add_value('sku', main_id)
            loader.add_value('identifier', main_id)
            loader.add_value('category', response.meta.get('category'))
            loader.add_value('image_url', image_url)
            stock = response.xpath('//div[@id="var-prices"]/div[@class="stock"]/text()').re('In Stock')
            if not stock:
                loader.add_value('stock', 0)

            item = loader.load_item()

            options = response.xpath('//form[contains(@id, "add")]/select/option')
            if options:
                for option in options:
                    option_id = option.xpath('@value').extract()[0]
                    option_price = response.xpath('//div[@id="price_'+option_id+'"]//div[@class="pmleft"]/text()').extract()[0]
                    option_name = option.xpath('text()').extract()[0]

                    loader = ProductLoader(item=Product(item), response=response)
                    loader.add_value('name', name + ' ' + option_name)
                    loader.add_value('price', option_price)
                    loader.add_value('category', response.meta.get('category'))
                    loader.add_value('identifier', main_id + '-' + option_id)
                    loader.add_value('sku', option_name.split(' - ')[-1])
                    stock = response.xpath('//div[@id="stock_'+option_id+'"]//text()').re('In Stock')
                    if not stock:
                        loader.add_value('stock', 0)
                    yield loader.load_item()
            else:
                size = response.xpath('//div[@id="product_size"]/text()').extract()
                if size:
                    size = size[0]
                    item['name'] += ' ' + size
                    item['sku'] = size.split(' - ')[-1]
                yield item

import re
import os
import csv
import shutil

from cStringIO import StringIO

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)

from scrapy.http import Request, HtmlResponse


HERE = os.path.abspath(os.path.dirname(__file__))


class SizzleSpider(BaseSpider):
    name = 'le_creuset-sizzle.co.uk'
    allowed_domains = ['sizzle.co.uk']
    start_urls = ('https://sizzle.co.uk/search?entry=le+creuset&per-page=360',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = [] # hxs.select('').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        products = hxs.select('//li[contains(@class,"shelf-product")]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        sku = hxs.select('//div/@data-sku').extract()[0].strip()
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)
        name = hxs.select('//h1[@data-test="name"]/text()').extract()[0].strip()
        loader.add_value('name', name)
        loader.add_value('category', 'Le Creuset')
        loader.add_xpath('image_url', '//img/@ds-product-image')
        loader.add_value('brand', 'Le Creuset')
        loader.add_value('url', response.url)
        
        price = hxs.select('//meta[@itemprop="price"]/@content').extract()
        
        price = price[0].strip() if price else '0.00'
        loader.add_value('price', price)
        stock = hxs.select('//span[@class="is-instock"]/span/text()').extract()
        if stock:
            stock_amount = re.search('(\d)+ in stock', stock[0])
            if stock_amount:
                loader.add_value('stock', stock_amount.group(1))
        else:
            loader.add_value('stock', 0)
        price = loader.get_output_value('price')
        if price:
            price = Decimal(price)
            if price < 29.0:
                loader.add_value('shipping_cost', '2.99')
        yield loader.load_item()

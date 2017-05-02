import os
import re
import json
import csv
import urlparse

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class MyTheresaSpider(BaseSpider):
    name = 'stylebop-mytheresa.com'
    allowed_domains = ['mytheresa.com']
    start_urls = ['http://www.mytheresa.com/en-de/mzi18n/storeswitch/selectorredirect/?redirectPath=/en-us/&country=US']

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
 
        yield Request("http://www.mytheresa.com/en-us", callback=self.parse_site)

    def parse_site(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//li[contains(@class, "parent")]/a[span[not(contains(text(), "Designers"))]]/@href').extract()
        for category in categories:
            yield Request(category, callback=self.parse_site)

        sub_categories = hxs.select('//li[contains(@class, "level2")]/a/@href').extract()
        for sub_category in sub_categories:
            yield Request(sub_category+'?p=1', dont_filter=True, callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
 
        category = hxs.select('//div[@class="col-left sidebar"]//div[@class="block-title"]/h1/text()').extract()[0]
 
        products = hxs.select('//h3[@class="product-name"]/a/@href').extract()
        for product in products:
            yield Request(product, callback=self.parse_product, meta={'category':category})

        next = hxs.select('//a[@class="next i-next"]/@href').extract()
        if next:
            parsed = urlparse.urlparse(response.url)
            params = urlparse.parse_qs(parsed.query)
            current_page = 'p=' + params['p'][0]
            next_page = 'p=' + str(int(params['p'][0])+1)
            yield Request(response.url.replace(current_page, next_page), callback=self.parse_category)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        meta = response.meta

        loader = ProductLoader(response=response, item=Product())
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_xpath('sku', '//h3[@class="sku-number"]/text()')
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        
        price = hxs.select('//p[@class="special-price"]/span[@class="price"]/text()').extract()
        if price:
            price = extract_price(price[0])
        else:
            price = hxs.select('//span[@class="price"]/text()').extract()
            if price:
                price = extract_price(price[0])
            else:
                price = 0
            
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_xpath('image_url', '//img[@id="main-image-image"]/@src')
        loader.add_xpath('brand', '//a[@itemprop="brand"]/text()')
        category = hxs.select('//div[@class="breadcrumbs"]/ul/li/a/span/text()').extract()[1]
        loader.add_value('category', meta['category'])
        loader.add_value('shipping_cost', 25)
        sold_out = hxs.select('//button[@class="btn-cart soldout"]')
        if sold_out:
            loader.add_value('stock', 0)
        yield loader.load_item()

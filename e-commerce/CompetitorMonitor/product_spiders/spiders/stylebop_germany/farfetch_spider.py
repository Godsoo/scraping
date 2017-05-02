import os
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, url_query_parameter
from product_spiders.utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class FarfetchSpider(BaseSpider):
    name = 'stylebop-germany-farfetch.com'
    allowed_domains = ['farfetch.com']
    rows = 120
    start_urls = ['http://www.farfetch.com/changecountry?ffref=hd']

    def parse(self, response):
        yield Request('http://www.farfetch.com/changecountry/77', callback=self.parse2)

    def parse2(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[contains(@class, "header-mobile-menu")]/li/ul/li/a[@href!="#"]')
        categories += hxs.select('//ul[@class="header-mobile-submenu"]/li/a[@href!="#"]')
        for category in categories:
            category_name = ''.join(category.select('text()').extract()).strip()
            category_url = urljoin_rfc(base_url, category.select('@href').extract()[0])
            yield Request(category_url, meta={'category': category_name}, callback=self.parse2)

        products = hxs.select('//div[@class="listing-item-content-box"]/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product, meta=response.meta)

        _next = hxs.select('//a[@id="PagingSelectorItemNext"]/@href').extract()
        if _next:
            yield Request(urljoin_rfc(base_url, _next[0]), meta=response.meta, callback=self.parse2)

    @staticmethod
    def parse_product(response):
        hxs = HtmlXPathSelector(response)
        l = ProductLoader(item=Product(), response=response)
        identifier = hxs.select('//p[@class="mt10"]/text()').extract()[0].strip().split('ID: ')[-1]
        store_id = hxs.select('//input[@id="StoreId"]/@value').extract()
        store_id = store_id[0] if store_id else ''
        l.add_value('identifier', identifier + '-' + store_id)
        l.add_value('sku', identifier)
        brand = hxs.select('//h1[@itemprop="brand"]/a/text()').extract()
        if brand:
            brand = brand[0].strip()
        else:
            brand = ''
        l.add_value('brand', brand)
        name = ''.join(hxs.select('//h2[@itemprop="name"]/text()').extract()).strip()
        l.add_value('name', name)
        l.add_value('url', response.url)
        image_url = hxs.select('//img[@class="responsive"]/@data-large').extract()
        if image_url:
            l.add_value('image_url', image_url[0])
        l.add_value('category', response.meta['category'])
        price = hxs.select('//span[@itemprop="price"]/text()').extract()
        if price:
            price = extract_price(price[0])
        else:
            price = hxs.select('//span[@class="color-red listing-sale"]/text()').extract()
            if price:
                price = extract_price(price[0])
            else:
                price = 0
        l.add_value('price', price)
        if not price:
            l.add_value('stock', 0)
        yield l.load_item()

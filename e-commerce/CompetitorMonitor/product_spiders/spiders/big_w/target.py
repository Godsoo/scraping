# -*- coding: utf-8 -*-
import scrapy
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
import json
from decimal import Decimal

from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class SupplementSpider(BaseSpider):
    name = 'bigw_target.com.au'
    allowed_domains = ['www.target.com.au']
    start_urls = ['http://www.target.com.au']


    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        urls_list = hxs.select('//ul[@class="mm-Departments mm-Departments--horizontal"]/li')
        for url_list in urls_list:
            links = url_list.select('//div[@class="mm-Departments-categoriesInner"]//a/@href').extract()
            for link in links:
                yield Request(urljoin_rfc(base_url, link), callback=self.parse_data)


    def parse_data(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        item_links = hxs.select('//h3[@class="name-heading"]/a/@href').extract()
        for item_link in item_links:
            yield Request(urljoin_rfc(base_url, item_link), callback=self.parse_page)
        pagination = ''
        try:
            pagination = hxs.select('//ul[@class="pager pager-pages"]//a[@title="Next Page"]/@href').extract()[0]
        except: pass
        if pagination:
            yield Request(urljoin_rfc(base_url,pagination), callback=self.parse_data)


    def parse_page(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        identifier = hxs.select('//input[@name="productCodePost"]/@value').extract()
        if not identifier:
            identifier = hxs.select('//input[@name="productCode"]/@value').extract()

        active_options = hxs.select('//li[contains(@class, "classification-option") and contains(@class, "active")]/a/text()').extract()
        active_options += hxs.select('//li[contains(@class, "swat-list-item-active")]/a/@title').extract()

        item_dict = json.loads(hxs.select('//div[@class="prod-detail"]/@data-ec-product').extract()[0])
        sizes = hxs.select('//ul[@class="classification-list var-change-list"]/li[@class="classification-option prod-var-item var-change-item "]/a/text()').extract()
     
        price = item_dict['price']
        brand = item_dict['brand']
        sku = item_dict['id']
        image_url = hxs.select('/html/head/meta[@property="og:image"]/@content').extract()
        if image_url:
            image_url = image_url[0]
        try:
            stock = hxs.select('//div[@itemprop="availability"]/text()').extract()[0]
        except:
            stock = hxs.select('//div[@class="in-stock"]/text()').extract()[0]
        categories_list = hxs.select('//div[@class="breadcrumb hfma"]/ul/li//span[@itemprop="title"]/text()')[1:-1].extract()


        loader = ProductLoader(item=Product(), response=response)
        title = hxs.select('//h1[@itemprop="name"]/text()').extract()[0]
        if active_options:
            size = hxs.select('//li[contains(@class, "classification-option") and contains(@class, "active")]/a/text()').extract()
            size = ' '.join(size)
            if not title.upper().endswith(size.strip().upper()):
                title += ' ' + size

        loader.add_value('name', title)
        loader.add_value('price', price)
        loader.add_value('brand', brand)
        loader.add_value('sku', sku)
        loader.add_value('category', categories_list)
        loader.add_value('image_url', image_url)
        loader.add_value('url', response.url)
        if 'In Stock Online' not in stock:
            loader.add_value('stock', 0)
        loader.add_value('identifier', identifier)
        item = loader.load_item()

        colors = hxs.select('//div[@class="prod-var-group"]/ul[@class="swat-list swat-list-colour var-change-list"]/li/a/@href').extract()
        if colors:
            for color in colors:
                yield Request(urljoin_rfc(base_url, color), callback=self.parse_page)

        sizes = hxs.select('//li[contains(@class, "classification-option")]/a/@href').extract()
        if sizes:
            for size in sizes:
                yield Request(urljoin_rfc(base_url, size), callback=self.parse_page)

        if (colors or sizes) and active_options:
            yield item
        
        if not colors and not sizes:
            yield item

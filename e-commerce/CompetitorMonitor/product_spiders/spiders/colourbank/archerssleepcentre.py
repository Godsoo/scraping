# -*- coding: utf-8 -*-
from collections import defaultdict
import urlparse

import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price


class ArcherssleepcentreSpider(BaseSpider):
    name = 'archerssleepcentre'
    allowed_domains = [
        'archerssleepcentre.co.uk',
    ]
    start_urls = ['http://www.archerssleepcentre.co.uk/']

    products_regex = re.compile(r'''(?s)var\s+products_json\s*=\s*(\{.*?\});''')

    visited = defaultdict(int)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # we extract the categories urls
        categories = hxs.select("//div[@id='navigation']//li/a/@href").extract()
        for category in categories:
            yield Request(
                urlparse.urljoin(response.url, category),
                callback=self.parse_category
            )

    def parse_category(self, response):
        """
        While parsing a category page we need to look after a product or category list
        """
        hxs = HtmlXPathSelector(response)

        # products
        for product_url in hxs.select(
                "//ol[contains(concat('',@class,''), 'product')]//div[@class='info']//a/@href").extract():
            yield Request(
                urlparse.urljoin(get_base_url(response), product_url),
                callback=self.parse_product
            )

        # sub categories
        for category_url in hxs.select("//ol[@id='subcats']//li/a/@href").extract():
            yield Request(
                urlparse.urljoin(response.url, category_url),
                callback=self.parse_category
            )

        # sub-sub categories
        for category_url in hxs.select("//ol[contains(@class, 'product-grid') or contains(@class, 'product-list')]/li"
                                       "/h2/a/@href").extract():
            yield Request(
                urlparse.urljoin(response.url, category_url),
                callback=self.parse_category
            )

        # next page
        next_page_url_list = hxs.select("//a[@class='next']/@href").extract()
        if next_page_url_list:
            yield Request(
                urlparse.urljoin(get_base_url(response), next_page_url_list[0]),
                callback=self.parse_category
            )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)

        price = ''.join(hxs.select("//div[@id='prices']//span[@class='sale']//text()").extract())
        # price = ''.join(re.findall('([\d\.,]+)', price))
        price = extract_price(price)
        loader.add_value('price', price)

        loader.add_value('url', response.url)
        loader.add_xpath('name', '//div[@id="product_top_wrap"]/h1/text()')
        if not price:
            stock = '0'
        else:
            stock = '1'
        loader.add_value('stock', stock)

        loader.add_xpath(
            'category',
            '//ul[@class="crumbs"]/li/a//text()'
        )
        loader.add_value('shipping_cost', "0")
        product_id = ''.join(hxs.select("//input[@name='productID']/@value").extract())
        loader.add_value('sku', product_id)
        loader.add_value('identifier', product_id)

        loader.add_xpath('image_url', "//div[@id='prodMainImage0']//img//@src")

        return loader.load_item()
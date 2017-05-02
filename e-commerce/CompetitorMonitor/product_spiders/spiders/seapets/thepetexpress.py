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

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class thepetexpress_spider(BaseSpider):
    name = 'thepetexpress.co.uk'
    allowed_domains = ['thepetexpress.co.uk', 'www.thepetexpress.co.uk']
    start_urls = ('http://www.thepetexpress.co.uk/',)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        # categories
        categories = hxs.select(u'//nav[@class="cat"]/ul/li/ul/li/a/@href').extract()
        categories += hxs.select('//*[contains(@class, "category_short")]'
                                 '/*[@class="cat_header"]//a/@href').extract()
        for url in categories:
            url = urljoin_rfc(get_base_url(response), url + u'?sort=titledesc')
            yield Request(url)

        # pagination
        next_page = hxs.select(u'//a[@class="nxt"]/@href').extract()
        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(next_page)

        # products
        products = hxs.select(u'//div[@class="products"]//a/@href').extract()
        for url in set(products):
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        try:
            image_url = hxs.select('//div[@id="product"]'
                                   '/div[@class="image_wrapper"]'
                                   '//a/img/@src').extract().pop().strip()
            image_url = urljoin_rfc(base_url, image_url)
        except:
            image_url = ''

        identifier = hxs.select('//form//input[@name="item_id"]'
                                '/@value').extract()

        if not identifier:
            identifier = hxs.select('//form/@name').re(r'frm_buy_(\d+)')

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        loader.add_value('identifier', identifier[0])
        loader.add_xpath('name', u'//div[@id="product"]/h1/text()')
        loader.add_value('image_url', image_url)
        loader.add_xpath('price', u'//p[@class="price"]/span[@class="our_price"]/text()')
        if loader.get_output_value('price'):
            yield loader.load_item()

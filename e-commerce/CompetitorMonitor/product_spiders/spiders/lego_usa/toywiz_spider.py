# -*- coding: utf-8 -*-

import os
import re

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class ToywizSpider(CrawlSpider):
    name = 'legousa-toywiz.com'
    allowed_domains = ['toywiz.com']
    start_urls = ['http://toywiz.com/lego']
    _re_sku = re.compile(r'(\d{3,})')

    # Map deviation screenshot feature
    #map_deviation_detection = True
    #map_deviation_csv = os.path.join(HERE, 'toywiz_map_deviation.csv')

    categories = LinkExtractor(restrict_css='.catList')
    products = LinkExtractor(restrict_css='.product')
    
    rules = (
        Rule(categories, callback='parse_category', follow=True),
        Rule(products, callback='parse_product')
        )
    
    def parse_category(self, response):
        urls = response.xpath('//script/text()').re("var desc = '(.+)?';")
        for url in urls:
            yield Request(response.urljoin(url))
        
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        try:
            identifier = response.xpath('//dd[@data-product-sku]/text()').extract()[0]
            name = response.xpath('//h1[@itemprop="name"]/text()').extract()[0]
        except:
            return

        loader = ProductLoader(item=Product(), response=response)

        sku = self._re_sku.findall(name)
        sku = sku[0] if sku else ''

        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        loader.add_xpath('brand', '//h2[@itemprop="brand"]//span/text()')
        loader.add_css('category', 'li.breadcrumb:last-child a::text')
        loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        loader.add_xpath('price', '//meta[@itemprop="price"]/@content')
        loader.add_value('price', '')
        loader.add_xpath('image_url', '//a[@id="image-zoom"]/@href')

        yield loader.load_item()

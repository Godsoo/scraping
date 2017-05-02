from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

import re

class PowerToolsUK(BaseSpider):
    name = 'powertoolsuk.co.uk'
    allow_domains = ['powertoolsuk.co.uk']
    start_urls = ['http://www.powertoolsuk.co.uk/']
    
    def parse(self, response):
        base_url = get_base_url(response)
        menu = re.findall('wpPopupMenuContent = "(.+)"', response.body)[0].replace('\\', '')
        hxs = HtmlXPathSelector(text=menu)
        for url in hxs.select('//a/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_category)
            
    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//h2[@class="product-name"]/a/@href').extract():
            yield Request(url, callback=self.parse_product)
        for url in hxs.select('//a[@title="Next"]/@href').extract():
            yield Request(url, callback=self.parse_category)
            
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(selector=hxs, item=Product())
        loader.add_xpath('name', '//h1/text()')
        loader.add_xpath('price', '//span[contains(@id, "price-including-tax")]/text()')
        stock = 1 if hxs.select('//span[text() = "In stock"]') else 0
        loader.add_value('stock', stock)
        loader.add_xpath('category', '//div[@class="breadcrumbs"]//li[@class!="home"]/a//text()')
        loader.add_xpath('brand', '//meta[@itemprop="brand"]/@content')
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_xpath('sku', '//meta[@itemprop="sku"]/@content')
        loader.add_value('url', response.url)
        loader.add_xpath('image_url', '//img[@id="image-main"]/@src')
        yield loader.load_item()

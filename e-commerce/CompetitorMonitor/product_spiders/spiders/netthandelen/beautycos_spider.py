# -*- coding: utf8 -*-
import os
import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class BeautycosSpider(BaseSpider):
    name = 'beautycos.dk'
    allowed_domains = ['beautycos.dk']
    start_urls = ['http://www.beautycos.dk']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//form/select/option/@value').extract()
        for category in categories:
            yield Request('http://www.beautycos.dk/group.asp?group=' + category, callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//table[@class="group-list"]/tr/td/table/tr/td[@id="group"]')
        if products:
            for product in products:
                url = urljoin_rfc(get_base_url(response), ''.join(product.select('font/a[1]/@href').extract()))
                yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        identifier = hxs.select('//input[@name="product"]/@value').extract()
        if not identifier:
            identifier = re.search(r'product=(.*)', response.url).groups()[0]
        loader.add_value('identifier', identifier)
        loader.add_xpath('name', '//*[@id="header"]/text()')
        loader.add_xpath('brand', '//a[@class="hilight"]/text()')
        loader.add_value('url', response.url)
        price = hxs.select('//*[@id="productdata"]//span[@class="price"]/text()').extract()
        if not price:
            price = hxs.select('//*[@id="productdesc"]//font/text()').re(u"Værdi: (.+)")
        if not price:
            price = hxs.select('//*[@id="productdesc"]//font/text()').re(u"Vejl. udsalgspris: (.+)")
        price = ''.join(price).replace('.', '').replace(',', '.')
        loader.add_value('price', price)
        loader.add_xpath('sku', '//input[@name="product"]/@value')
        loader.add_xpath('category', u'//span[@id="productnavgroup"]/a[1]/text()')
        img = hxs.select(u'//img[@id="productimg"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
        yield loader.load_item()

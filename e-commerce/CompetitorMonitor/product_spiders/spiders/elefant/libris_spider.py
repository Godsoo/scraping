# -*- coding: utf-8 -*-
import os
import re

from scrapy import log

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url


from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class LibrisSpider(BaseSpider):
    name = 'elefant-libris.ro'
    allowed_domains = ['libris.ro']
    start_urls = ['http://www.libris.ro']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//div[@id="mainMenu"]/nav/a/@href').extract()
        categories += hxs.select('//div[@id="leftcolumn"]/ul/li/a/@href').extract()
        categories += hxs.select('//div[@id="leftcolumn"]/div/div[@class="categ"]//a/@href').extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            yield Request(url)

        products = hxs.select('//div/ul[@class="grid"]/li/h4/a/@href').extract()
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, callback=self.parse_product)

        next = hxs.select(u'//a[text()="»"]/@href').extract()
        if next:
            next = urljoin_rfc(get_base_url(response), next[0])
            yield Request(next)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//div[@class="col_right"]/h1/text()')
        loader.add_value('url', response.url)
        brand = hxs.select('//p[span[contains(text(), "Editura")]]/a/span/text()').extract()
        loader.add_value('brand', brand)
        categories = hxs.select('//h4[@class="bread"]/a/text()').extract()
        for category in categories:
            loader.add_value('category', category)
        sku = hxs.select('//p[span[contains(text(), "Cod")]]/text()').extract()
        if sku:
            sku = sku[0].strip()
            if len(''.join(re.findall('[a-zA-Z]+', ''.join(sku[:3]))))==3:
                sku = sku[3:]

        loader.add_value('sku', sku)
        loader.add_value('identifier', re.findall('--p(.*).html', response.url)[0])
        image_url = hxs.select('//div[@id="image-block"]/a/img/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[-1])

        price = ''.join(hxs.select('//p[@class="pret"]/text()').extract()).strip()
        loader.add_value('price', price)

        if not loader.get_output_value('price'):
            loadet.add_value('stock', 0)

        yield loader.load_item()

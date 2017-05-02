# -*- coding: utf8 -*-
import os
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class BeautycosSpider(BaseSpider):
    name = 'cocopanda-beautycos.dk'
    allowed_domains = ['beautycos.dk']
    start_urls = ['http://www.beautycos.dk']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//form/select/option/@value').extract()
        for category in categories:
            yield Request('http://www.beautycos.dk/group.asp?group=' + category, callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        meta = {}
        products = hxs.select('//table[@class="group-list"]/tr/td/table/tr/td[@id="group" and font]')
        if products:
            for product in products:
                category = hxs.select('//b[@id="header"]/text()').extract()[0]                 
                brand = hxs.select('//span[@id="productnavgroup"]/a/text()').extract()[0]
                identifier = ''.join(product.select('font/a[1]/@href').extract()).split('product=')[-1]
                image_url = urljoin_rfc(get_base_url(response), product.select('font/a/img/@src').extract()[0])
                url = urljoin_rfc(get_base_url(response), ''.join(product.select('font/a[1]/@href').extract()))
                price = ''.join(product.select('font/b//text()').extract()).replace('.', '').replace(',', '.')
                if 'Pris' not in price:  # == 'Midlertidig udsolgt':
                    meta['image_url'] = image_url
                    meta['identifier'] = identifier
                    meta['brand'] = brand
                    meta['category'] = category
                    yield Request(url, callback=self.parse_product, meta=meta)
                else:
                    loader = ProductLoader(item=Product(), selector=product)
                    loader.add_xpath('name', 'font/a/text()')
                    loader.add_value('identifier', identifier)
                    loader.add_value('url', url)
                    loader.add_value('category', category)
                    loader.add_value('brand', brand)
                    loader.add_value('price', price)
                    loader.add_value('image_url', image_url)
                    yield loader.load_item()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//*[@id="header"]/text()')
        loader.add_value('url', response.url)
        price = hxs.select('//*[@id="productdata"]//span[@class="price"]/text()').extract()
        if not price:
            price = hxs.select('//*[@id="productdesc"]//font/text()').re(u"Værdi: (.+)")
        if not price:
            price = hxs.select('//*[@id="productdesc"]//font/text()').re(u"Vejl. udsalgspris: (.+)")
        price = ''.join(price).replace('.', '').replace(',', '.')
        loader.add_value('price', price)
        loader.add_value('identifier', meta.get('identifier',''))
        loader.add_value('image_url', meta.get('image_url',''))
        loader.add_value('brand', meta.get('brand',''))
        loader.add_value('category', meta.get('category',''))
        yield loader.load_item()

# -*- coding: utf-8 -*-
import os
from decimal import Decimal

from scrapy import Spider
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class ToolStopSpider(Spider):
    name = 'powertools2u-toolstop.co.uk'
    allowed_domains = ['toolstop.co.uk']
    start_urls = ['http://www.toolstop.co.uk/?gl=gb&currency=GBP']

    def parse(self, response):
        yield Request('http://www.toolstop.co.uk/brands', callback=self.parse_main)

    def parse_main(self, response):
        base_url = get_base_url(response)
        brands = response.xpath('//p[@class="brand_name"]/a/@href').extract()
        categories = response.xpath('//ul[@class="category_link"]//a/@href').extract()
        for url in brands + categories:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_main)

        products = response.xpath('//div[@class="liked_product_name"]//a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        loader.add_xpath('price', '//meta[@itemprop="exvatprice"]/@content')
        loader.add_value('url', response.url)
        loader.add_xpath('brand', '//div[@id="brandlink"]//img/@alt')
        loader.add_xpath('sku', '//span[@class="barcode"]/text()')
        if not loader.get_output_value('sku'):
            loader.add_xpath('sku', '//meta[@itemprop="gtin13"]/@content')

        loader.add_value('identifier', response.url.split('p')[-1])

        image_url = response.xpath('//meta[@property="og:image"]/@content').extract()[0]
        loader.add_value('image_url', urljoin_rfc(base_url, image_url))
        price = loader.get_output_value('price')
        if price < Decimal(25):
            loader.add_value('shipping_cost', '6.95')
        else:
            loader.add_value('shipping_cost', '0')

        categories = response.xpath('//ul[@id="breadcrumb"]//a/text()').extract()
        categories = [x.strip() for x in categories if x.lower().strip() != 'home'][:3]
        loader.add_value('category', categories)

        if not response.xpath('//h4[@class="product_instock"]') and not response.xpath('//button[@class="buynow"]'):
            loader.add_value('stock', 0)

        yield loader.load_item()

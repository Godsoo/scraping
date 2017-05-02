# -*- coding: utf-8 -*-
import os
from decimal import Decimal

from product_spiders.base_spiders.primary_spider import PrimarySpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class ToolStopSpider(PrimarySpider):
    name = 'ffxtools-toolstop.co.uk'
    allowed_domains = ['toolstop.co.uk']
    start_urls = ['http://www.toolstop.co.uk/?gl=gb&currency=GBP']

    csv_file = 'toolstop.co.uk_products.csv'

    def parse(self, response):
        yield Request('http://www.toolstop.co.uk/brands', callback=self.parse_main)

    def parse_main(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        brands = hxs.select('//p[@class="brand_name"]/a/@href').extract()
        categories = hxs.select('//ul[@class="category_link"]//a/@href').extract()
        for url in brands + categories:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_main)

        products = hxs.select('//div[@class="liked_product_name"]//a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        loader.add_xpath('price', '//meta[@itemprop="price"]/@content')
        loader.add_value('url', response.url)
        loader.add_xpath('brand', '//div[@id="brandlink"]//img/@alt')
        loader.add_xpath('sku', '//span[@class="barcode"]/text()')
        if not loader.get_output_value('sku'):
            loader.add_xpath('sku', '//meta[@itemprop="gtin13"]/@content')

        loader.add_value('identifier', response.url.split('p')[-1])

        image_url = hxs.select('//meta[@property="og:image"]/@content').extract()[0]
        loader.add_value('image_url', urljoin_rfc(base_url, image_url))
        price = loader.get_output_value('price')
        if price < Decimal(25):
            loader.add_value('shipping_cost', '6.95')
        else:
            loader.add_value('shipping_cost', '0')

        categories = hxs.select('//ul[@id="breadcrumb"]//a/text()').extract()
        categories = [x.strip() for x in categories if x.lower().strip() != 'home'][:3]
        loader.add_value('category', categories)

        if not hxs.select('//h4[@class="product_instock"]') and not hxs.select('//button[@class="buynow"]'):
            loader.add_value('stock', 0)

        yield loader.load_item()

# -*- coding: utf-8 -*-
import os
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
from decimal import Decimal

HERE = os.path.abspath(os.path.dirname(__file__))


class ConradSpider(BaseSpider):
    name = u'conrad.de'
    allowed_domains = ['www.conrad.de']
    start_urls = ('http://www.conrad.de/ce/de/Search.html?search=LOGITECH&perPage=100',)

    map_products_csv = os.path.join(HERE, 'logitech_map_products.csv')
    map_price_field = 'map'
    map_join_on = [('sku', 'mpn'), ('sku', 'ean13')]

    def start_requests(self):

        for url in self.start_urls:
            yield Request(url)

        with open(HERE + '/logitech_extra_products.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Conrad'] != 'No Match':
                    yield Request(row['Conrad'], callback=self.parse_product, meta={'sku':row['sku'], 'brand':row['brand']})

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//*[@id="list-product-list"]//span[@class="teaserlink"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        for url in hxs.select('//div[@class="page-navigation"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//a[@name="head_detail"]/text()').extract()[0]
        loader.add_value('name', name)
        identifier = hxs.select('//meta[@name="WT.pn_sku"]/@content').extract()[0]
        loader.add_value('identifier', identifier)

        sku = response.meta.get('sku', '')
        if sku:
            loader.add_value('sku', sku)
            loader.add_value('brand', response.meta.get('brand', ''))
        else:
            sku = hxs.select('//*[@id="mc_info_teilenummer"]/text()').extract()
            if sku:
                loader.add_value('sku', sku[0])
            loader.add_value('brand', 'Logitech')

        loader.add_value('url', response.url)
        image_url = hxs.select('//*[@id="BigProductImage"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        price = hxs.select('//span[@class="price"]/text()').extract()
        price = extract_price(price[0])
        loader.add_value('price', price)
        in_stock = hxs.select('//*[@id="mc_info_lieferbarkeit"]/text()').extract()[0].strip()
        if in_stock == 'ausverkauft':
            loader.add_value('stock', 0)
        category = hxs.select('//*[@id="ariadne"]/a[3]/text()').extract()
        if category:
            loader.add_value('category', category[0])
        yield loader.load_item()

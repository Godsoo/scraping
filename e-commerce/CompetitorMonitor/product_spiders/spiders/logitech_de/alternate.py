# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
import re
import os
import csv

HERE = os.path.abspath(os.path.dirname(__file__))


class AlternateSpider(BaseSpider):
    name = u'alternate.de'
    allowed_domains = ['www.alternate.de']
    start_urls = ('http://www.alternate.de/html/search.html?query=Logitech',)

    map_products_csv = os.path.join(HERE, 'logitech_map_products.csv')
    map_price_field = 'map'
    map_join_on = [('identifier', 'mpn'), ('identifier', 'ean13')]

    used_skus = []

    def start_requests(self):

        for url in self.start_urls:
            yield Request(url)

        with open(HERE + '/logitech_extra_products.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield Request(row['Alternate'], callback=self.parse_product, meta={'sku':row['sku'], 'brand':row['brand']})

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//a[@class="productLink"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        for url in hxs.select('//div[@class="paging"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//h1/span/text()').extract()
        loader.add_value('name', ' '.join(name))
        try:
            identifier = hxs.select('//var[@id="expressTickerProductId"]/text()').extract()[0]
        except IndexError:
            return
        match = re.search(r"ccs_cc_args\.push\(\['upcean', '(.*?)'\]\);", response.body)
        sku = response.meta.get('sku', '')
        if sku:
            loader.add_value('sku', sku)
            loader.add_value('brand', response.meta.get('brand', ''))
            loader.add_value('identifier', identifier)
        else:
            if match:
                sku = match.group(1).strip()
                loader.add_value('sku', sku)
            if sku != '' and sku not in self.used_skus:
                self.used_skus.append(sku)
                loader.add_value('identifier', sku)
            else:
                loader.add_value('identifier', identifier)
            loader.add_value('brand', 'Logitech')
        loader.add_value('url', response.url)
        image_url = hxs.select('//meta[@itemprop="image"]/@content').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        price = hxs.select('//span[@itemprop="price"]/@content').extract()
        price = extract_price(price[0])
        loader.add_value('price', price)
        in_stock = hxs.select('//meta[@itemprop="availability"]/@content').extract()[0].strip()
        if in_stock != 'InStock':
            loader.add_value('stock', 0)
        category = hxs.select('//div[@class="breadCrumbs"]//a/span/text()').extract()
        if category:
            loader.add_value('category', category[-2])
        yield loader.load_item()

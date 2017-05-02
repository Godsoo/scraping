# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price_eu as extract_price
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter
import re


class ClimandoItSpider(BaseSpider):
    name = u'climando.it'
    allowed_domains = ['www.climando.it']
    start_urls = ('http://www.climando.it', )

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        url = 'http://www.climando.it/modules/blocklayered/blocklayered-ajax.php?n=100&id_category_layered='
        for cat in hxs.select('//ul[@class="tree dhtml"]/li/a/@href').re(r'(\d+)'):
            yield Request(url + cat, callback=self.parse_product_list)

    def parse_product_list(self, response):
        i = 0
        for match in re.finditer(r'(?si)<h5>.+?href=\\"(.*?)\\"', response.body):
            i += 1
            url = match.group(1)
            yield Request(url.replace('\\', ''), callback=self.parse_product)
        if i == 100:
            page = int(url_query_parameter(response.url, 'p', '1'))
            page += 1
            url = add_or_replace_parameter(response.url, 'p', str(page))
            yield Request(url, callback=self.parse_product_list)

    @staticmethod
    def parse_product(response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//span[@itemprop="name"]/text()').extract()[0]
        loader.add_value('name', name)
        identifier = hxs.select('//input[@name="id_product"]/@value').extract()[0]
        loader.add_value('identifier', identifier)
        sku = hxs.select('//span[@class="editable"]/text()').extract()
        if sku:
            loader.add_value('sku', sku[0])
        loader.add_value('url', response.url)
        image_url = hxs.select('//*[@id="big_pic"]/@href').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        price = hxs.select('//*[@id="our_price_display"]/text()').extract()
        if not price:
            return
        price = extract_price(price[0])
        loader.add_value('price', price)
        brand = hxs.select('//meta[@itemprop="manufacturer"]/@content').extract()
        if brand:
            loader.add_value('brand', brand[0])
        out_of_stock = hxs.select('//*[@id="set-quantity"]/@style').extract()
        if out_of_stock:
            loader.add_value('stock', 0)
        category = hxs.select('//div[@class="breadcrumb"]/a[2]/text()').extract()
        if category:
            loader.add_value('category', category[0])
        yield loader.load_item()

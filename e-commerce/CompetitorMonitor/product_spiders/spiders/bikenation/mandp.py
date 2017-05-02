# -*- coding: utf-8 -*-
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import FormRequest, Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
from datetime import datetime
import os
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider

HERE = os.path.abspath(os.path.dirname(__file__))
fname = os.path.join(HERE, 'mandp_products.csv')


class MandpSpider(BigSiteMethodSpider):
    name = u'mandp.co.uk'
    allowed_domains = ['www.mandp.co.uk']
    start_urls = ['http://www.mandp.co.uk']
    website_id = 638
    do_full_run = True
    full_crawl_day = 6
    do_retry = True
    max_retry_count = 15
    retry_sleep = 60
    domain = 'www.mandp.co.uk'
    all_products_file = os.path.join(HERE, 'mandp.csv')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@id="header-nav"]//a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category))

        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        next = hxs.select('//a[@class="next i-next"]/@href').extract()
        if next:
            next = urljoin_rfc(base_url, next[0])
            yield Request(next)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        identifier = hxs.select('//tr[th[contains(text(), "SKU")]]/td/text()').extract()
        if not identifier:
            return
        identifier = identifier[0].strip()
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        name = hxs.select('//span[@itemprop="name"]/text()').extract()[0].strip()
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        image_url = hxs.select('//img[@class="gallery-image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        category = hxs.select('//div[@class="breadcrumbs"]/ul/li/a/text()').extract()
        if category:
            loader.add_value('category', category[0])
        price = hxs.select('//span[@class="special-price"]/span[@class="price"]/text()').extract()
        if not price:
            price = hxs.select('//span[@class="regular-price"]/span[@class="price"]/text()').extract()
        price = extract_price(price[0])
        loader.add_value('price', price)
        brand = hxs.select('//tr[th[text()="Manufacturer"]]/td/text()').extract()
        if brand:
            loader.add_value('brand', brand[0])
        product = loader.load_item()

        yield product

# -*- coding: utf-8 -*-
import shutil
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from urllib import urlencode
import json
import os
import csv
from datetime import datetime, timedelta
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

here = os.path.abspath(os.path.dirname(__file__))


class Lensway(BaseSpider):
    name = "specsavers_sw-lensway.se"
    allowed_domains = ["lensway.se"]
    start_urls = ['http://www.lensway.se/kontaktlinser/endagslinser',
                  'http://www.lensway.se/kontaktlinser/veckolinser',
                  'http://www.lensway.se/kontaktlinser/manadslinser']

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        products = hxs.select("//ul[not(@style)][@id=\"productList\"][contains(concat(' ',normalize-space(@class),' '),\" product-list clearfix \")]/li[not(@style)][(contains(concat(' ',normalize-space(@class),' '),\" productItem \") and contains(concat(' ',normalize-space(@class),' '),\" grid_5 \"))]")
        for p in products:
            url = p.select(".//a[not(@id)][not(@style)][contains(concat(' ',normalize-space(@class),' '),\" content dispBl \")]/@href").extract()[0]
            yield Request(urljoin(base_url, url), callback=self.parse_product)
        next_pages = hxs.select('//div[@class="pagination-list fr"]/a/@href').extract()
        for n in next_pages:
            yield Request(response.url.split('?')[0] + n)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        name = hxs.select('//h1[@class="product-info-head"]/div[1]/text()').extract()
        name = ''.join(name).strip()
        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('name', name)
        loader.add_xpath('price', ".//span[not(@id)][not(@style)][contains(concat(' ',normalize-space(@class),' '),\" inline price bold productInfo-orgPrice product-info-price-current \")]/text()")
        image_url = hxs.select(".//div[not(@id)][not(@style)][contains(concat(' ',normalize-space(@class),' '),\" productPage_image_default \")]/img[1][not(@id)][not(@style)][contains(concat(' ',normalize-space(@class),' '),\" photo \")]/@src").extract()
        if image_url:
            loader.add_value('image_url', 'http:' + image_url[0])
        loader.add_xpath('brand', ".//dl[not(@id)][not(@class)][not(@style)]/dd[1][not(@id)][not(@class)][not(@style)]/text()")
        category = hxs.select(".//nav[not(@id)][not(@style)][contains(concat(' ',normalize-space(@class),' '),\" breadcrumbs module small \")]/div[2][not(@id)][not(@class)][not(@style)]/a[1][not(@id)][not(@class)][not(@style)]//text()").extract()
        if category:
            category = ''.join(category).strip()
            loader.add_value('category', category)
        loader.add_value('url', response.url)
        loader.add_value('identifier', response.url.split('/')[-1])

        if loader.get_output_value('price'):
            yield loader.load_item()

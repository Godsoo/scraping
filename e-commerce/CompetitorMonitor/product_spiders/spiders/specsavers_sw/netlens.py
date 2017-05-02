# -*- coding: utf-8 -*-
import shutil
import re
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


class NetLens(BaseSpider):
    name = "specsavers_sw-netlens"
    allowed_domains = ["netlens.se"]
    start_urls = ['http://www.netlens.se/alla-linser.php']

    def parse(self, response):

        categories = response.xpath('//li[a/text()="Linser"]//a/@href').extract()
        for category in categories:
            yield Request(category, callback=self.parse_products)

        search_url = 'http://www.netlens.se/speciallinser.php?searchpara='
        categories = response.xpath('//li[a/text()="Linser"]//label/@for').extract()
        for category in categories:
            yield Request(search_url + category, callback=self.parse_products)

    def parse_products(self, response):
        base_url = get_base_url(response)

        products = response.xpath('//table[@class="productListing"]/tr')
        for p in products:
            loader = ProductLoader(item=Product(), selector=p)
            try:
                url = p.select('.//a/@href').extract()[0]
            except IndexError:
                continue
            name = p.select('.//a[@class="boxtitle"]//text()').extract()[0]
            price = p.select('.//span[@class="boxprice"]/text()').extract()[0]
            image_url = p.select('.//img/@src').extract()[0]
            identifier = re.search('products_id=(\d+)', url).groups()[0] 
            loader.add_value('url', url)
            loader.add_value('price', price)
            loader.add_value('name', name)
            loader.add_value('image_url', urljoin(base_url, image_url))
            loader.add_value('category', response.url.split('=')[1])
            loader.add_value('identifier', identifier)
            yield Request(url, meta={'loader': loader}, callback=self.parse_brand)

    def parse_brand(self, response):
        loader = response.meta['loader']
        hxs = HtmlXPathSelector(response)
        try:
            brand = hxs.select('//table[@id="spectable"]/tr[4]/td[2]/text()').extract()
            loader.add_value('brand', brand[0])
        except IndexError:
            pass

        yield loader.load_item()

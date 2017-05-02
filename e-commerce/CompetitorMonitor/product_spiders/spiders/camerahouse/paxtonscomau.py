# -*- coding: utf-8 -*-
import csv
import hashlib
import os
import shutil
from datetime import datetime
import StringIO
import urlparse
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import CloseSpider
from scrapy import signals

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class PaxtonsSpider(BaseSpider):
    name = 'paxtons.com.au'
    allowed_domains = ['paxtons.com.au']
    start_urls = ['http://www.paxtons.com.au']

    next_page_regex = re.compile(r'window\.location\.assign\(\'(.*)\'\)')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # we extract the categories urls
        # categories = hxs.select("//a[@href[contains(., 'products.html')] and img]/@href").extract()
        categories = hxs.select('//ul[@class="nav"]//a/@href').extract()
        categories += hxs.select('//table[@class="templateTable"]//a/@href').extract()

        for category in categories:
            yield Request(
                urlparse.urljoin(response.url, category),
                callback=self.parse_results_list
            )

    def parse_results_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        category = hxs.select("//p[@class='pl_selected_item']/text()").extract()
        if not category:
            for url in hxs.select("//p[@class='pl_item']/a/@href").extract():
                yield Request(urlparse.urljoin(base_url, url), callback=self.parse_results_list)
            return

        # extract the product urls
        products_href = hxs.select(
            "//a[@rel='product' and img]/@href").extract()
        for href in products_href:
            url = urlparse.urljoin(get_base_url(response), href)
            yield Request(
                url,
                meta={'category': category[0].strip()},
                callback=self.parse_product
            )

        # extract next pages url
        next_page_href = hxs.select("//input[@title='Next']/@onclick").extract()
        for nhref in next_page_href:
            url = urlparse.urljoin(get_base_url(response), self.next_page_regex.findall(nhref)[0])
            yield Request(url, callback=self.parse_results_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        product_in_stock = hxs.select("//div[contains(concat('',@id), 'price_div')][1]/p//text()").extract()
        if product_in_stock:
            stock = '1'
        else:
            stock = '0'
        price = hxs.select("//div[contains(concat('',@id), 'price_div')][1]/p//meta[@itemprop='price']/@content").extract()
        if not price:
            price = ''.join([x.strip() for x in product_in_stock])
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        product_name = ' '.join(x.strip() for x in hxs.select("//h1//text()").extract() if x.strip())
        loader.add_value('name', product_name)
        loader.add_value('identifier', hashlib.md5(product_name.encode('utf-8')).hexdigest())
        loader.add_value('stock', stock)
        loader.add_value('category', response.meta['category'])
        loader.add_xpath('brand', "//h1/span[@class='brand']/text()")
        loader.add_value('shipping_cost', '10.0')
        sku_script = ''.join(hxs.select("//script[contains(., 'var manufacturer ')]/text()").extract())
        sku = re.findall(r'(\d+)', sku_script)
        loader.add_value('sku', sku)

        image_url = ''.join(hxs.select("(//img[@id='product_photo']/@source_to_be_lazy_loaded)[1]").extract())
        if not image_url.startswith('http://'):
            image_url = "http://{}".format(image_url)
        loader.add_value('image_url', image_url)
        yield loader.load_item()

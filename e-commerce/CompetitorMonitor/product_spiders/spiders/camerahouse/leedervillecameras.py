# -*- coding: utf-8 -*-
import csv
import json
import os
import shutil
from datetime import datetime
import StringIO
import urlparse
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector, Selector
from scrapy.http import Request, HtmlResponse, FormRequest, TextResponse
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import CloseSpider
from scrapy import signals

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class LeederVilleCamerasSpider(BaseSpider):
    name = 'leedervillecameras'
    allowed_domains = ['leedervillecameras.com.au', ]
    start_urls = ['http://www.leedervillecameras.com.au']

    products_regex = re.compile(r'''(?s)var\s+products_json\s*=\s*(\{.*?\});''')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # we extract the categories urls
        categories = hxs.select("//a[@class='show_all_cat']/@href").extract()
        categories.extend(hxs.select("//ul[@class='nav navbar-nav']/li[last() - 1]/a/@href").extract())
        for category in categories:
            yield Request(
                urlparse.urljoin(response.url, category),
                callback=self.parse_category
            )

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)

        products_href = response.xpath('//div[@id="products_container"]//a/@href').extract()
        for href in products_href:
            yield Request(
                urlparse.urljoin(get_base_url(response), href),
                callback=self.parse_product
            )

        category_id = ''.join(response.xpath("//span[@class='categ_checkbox checkbox selected']/@id").extract())
        count = response.css('input#count_fetcher::attr(value)').extract_first()
        # get next batch of products
        form_data = {
            'minPrice': '0',
            'maxPrice': '24999',
            'categories': '{}'.format(category_id),
            'from': '{}'.format(len(products_href)),
            'lcd_value': "",
            'mp_value': "",
            'oz_value': "",
            'ss_value': "",
            'ma_value': "",
            'cs_value': "",
            'fb_value': "",
            'rs_value': "",
            'action': "reset",
            'type': "opt",
            'count': count
        }
        yield FormRequest(
            url="http://www.leedervillecameras.com.au/products/ajax/getProducts",
            formdata=form_data,
            meta={'category_id': category_id, 'count': count},
            callback=self.parse_post_response
        )

    def parse_post_response(self, response):
        response_json = json.loads(response.body_as_unicode())

        hxs = Selector(text=response_json['html'])

        try:
            products_href = hxs.css('.product-item a::attr(href)').extract()
        except AttributeError:
            return

        for href in products_href:
            yield Request(
                urlparse.urljoin(get_base_url(response), href),
                callback=self.parse_product
            )

        category_id = response.meta['category_id']
        self.log(str(response_json['from']))
        self.log(str(response_json['from'] + len(products_href)))
        # get next batch of products
        form_data = {
            'minPrice': '0',
            'maxPrice': '24999',
            'categories': '{}'.format(category_id),
            'from': '{}'.format(response_json['from']),
            'lcd_value': "",
            'mp_value': "",
            'oz_value': "",
            'ss_value': "",
            'ma_value': "",
            'cs_value': "",
            'fb_value': "",
            'rs_value': "",
            'action': "reset",
            'type': "opt",
            'count': response.meta['count']
        }
        if products_href:
            yield FormRequest(
                url="http://www.leedervillecameras.com.au/products/ajax/getProducts",
                formdata=form_data,
                meta=response.meta,
                callback=self.parse_post_response
            )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        
        price = response.css('.prodprice span::text').extract_first()
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_xpath('name', "//h2/text()")
        loader.add_value('stock', '1')
        loader.add_xpath('category',
                         "//ol[@class='no-gutter breadcrumb']//li[2 < position() and position() < last()]//text()")
        loader.add_xpath('brand',
                         "//ol[@class='no-gutter breadcrumb']//li[3 < position() and position() < last()]//text()")
        loader.add_value('shipping_cost', "0.00")
        loader.add_xpath('sku', "//input[@name='product_id']/@value")
        loader.add_xpath('identifier', "//input[@name='product_id']/@value")
        if not loader.get_output_value('identifier'):
            return

        image_src = ''.join(hxs.select("//img[@id='prime_image']/@src").extract())
        image_url = urlparse.urljoin(get_base_url(response), image_src)
        loader.add_value('image_url', image_url)
        yield loader.load_item()

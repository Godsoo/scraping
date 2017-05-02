# -*- coding: utf-8 -*-
"""
Account: Lakeland
Name: lakeland-therange.co.uk
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4884
We are only monitoring specific categories for this site.

Original developer: Franco Almonacid <fmacr85@gmail.com>
"""

import re
import demjson
import paramiko
import os
import csv
from decimal import Decimal
from tempfile import NamedTemporaryFile

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.base_spiders import PrimarySpider
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

HERE = os.path.abspath(os.path.dirname(__file__))


class TheRangeSpider(PrimarySpider):
    name = 'lakeland-therange.co.uk'
    allowed_domains = ['therange.co.uk']
    csv_file = 'lakeland_therange_as_prim.csv'
    start_urls = ['https://www.therange.co.uk/']
    
    #user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:49.0) Gecko/20100101 Firefox/49.0'
    rotate_agent = True
    download_delay = 8
    handle_httpstatus_list = [405, 416]
    #custom_settings = {'RETRY_HTTP_CODES': [405, 416]}
                       #'HTTPERROR_ALLOWED_CODES': [405, 416]}
    
    def proxy_service_check_response(self, response):
        if response.xpath('//div[@id="distil_ident_block"]'):
            return True
        if response.status in [405, 416]:
            return True

    def parse(self, response):
        if 'distil_r_blocked' in response.url or response.status in self.handle_httpstatus_list:
            retries = response.meta.get('retries', 0)
            if retries < 50:
                self.log('Retrying %s (antibot protection)' %response.url)
                yield response.request.replace(meta={'retries':retries+1},
                                               dont_filter=True,
                                               url=response.meta.get('redirect_urls', [response.url])[0])
            else:
                self.log('Gave up retrying %s (antibot protection)' %response.url)
            return
        
        categories = response.css('ul.nav a::attr(href)').extract()
        for category in categories:
            yield Request(response.urljoin(category))

        products = response.css('li.product a::attr(href)').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product)

        next = response.xpath('//li[@class="curved_mini"]/a[contains(text(), "Next")]/@href').extract()
        if next:
            yield Request(response.urljoin(next[-1]))

        identifier = response.xpath('//div/@data-product-full-id').extract()
        if identifier:
            for item in self.parse_product(response):
                yield item

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        main_name = re.search('ecommerce.*name\': \'(.*?)\'', response.body, re.DOTALL).group(1)
        main_price = re.search('ecommerce.*price\': \'(.*?)\'', response.body, re.DOTALL).group(1)
        brand = re.search('ecommerce.*?brand\': \'(.*?)\'', response.body, re.DOTALL).group(1)
        identifier = response.xpath('//div/@data-product-full-id').extract()[0]

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('name', main_name)
        loader.add_value('url', response.url)
        loader.add_value('price', main_price)
        loader.add_xpath('image_url', '//meta[@property="og:image"]/@content')
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('brand', brand)
        for category in hxs.select('//div[@id="breadcrumb"]/ul[@id="crumbs"]/li/a/text()')[1:].extract():
            loader.add_value('category', category)

        options = hxs.select('//div[contains(@class, "element")]/select[@name="ProductID" and @id="select_size"]/option')

        for option in options:
            identifier = option.select('./@value')[0].extract()
            loader.replace_value('identifier', identifier)

            option_name, option_price = option.select('./text()')[0].extract().strip().split(' - ')
            loader.replace_value('name', '{} {}'.format(main_name, option_name))
            loader.replace_value('price', option_price)
            if loader.get_output_value('price')<50:
                loader.add_value('shipping_cost', 3.95)

            yield loader.load_item()

        if not options:
            if loader.get_output_value('price')<50:
                loader.add_value('shipping_cost', 3.95)
            yield loader.load_item()

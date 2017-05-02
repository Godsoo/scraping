import re
import os
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse, TextResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
import hashlib
from decimal import Decimal

import csv

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class PFJonesSpider(BaseSpider):
    name = 'towequipe-pfjones.co.uk'
    allowed_domains = ['pfjones.co.uk', 'www.pfjones.co.uk']
    start_urls = (u'http://www.pfjones.co.uk', )

    def start_requests(self):
        with open(os.path.join(HERE, 'products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row['SKU']
                url = u'http://www.pfjones.co.uk/?subcats=Y&status=A&pshort=Y&pfull=Y&pname=Y&pkeywords=Y&search_performed=Y&q=%(q)s' \
                      u'&cid=0&x=0&y=0&dispatch=products.search'

                yield Request(url % {'q': sku}, meta={'sku': sku, 'partn': row['partn'], 'postage': float(row['pfjones_postage'])})


    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        for product in self.parse_product(response):
            yield product

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        products = hxs.select(u'//td[@class="product-description"]')
        pr = None
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_value('name', product.select(u'./a/text()')[0].extract().strip())
            url = product.select(u'./a/@href')[0].extract()
            url = urljoin_rfc(get_base_url(response), url)
            loader.add_value('url', url)
            price = float(product.select(u'.//span[starts-with(@id,"sec_discounted") and @class="price"]/text()')[0].extract())
            price += response.meta['postage']
            loader.add_value('price', price)
            image_url = product.select(u'./preceding-sibling::td//img/@src')[0].extract()
            image_url = urljoin_rfc(get_base_url(response), image_url)
            loader.add_value('image_url', image_url)
            sku = product.select(u'./p[1]/text()')[0].extract()
            sku = re.search('CODE: (.*)', sku).group(1)
            log.msg('SKU: [%s == %s]' % (sku.lower(), response.meta['sku'].lower()))
            if sku.lower() == response.meta['sku'].lower():
                loader.add_value('sku', response.meta['partn'])
                loader.add_value('identifier', response.meta['partn'].lower())
                if pr is None or loader.get_output_value('price') < pr.get_output_value('price'):
                    pr = loader
                # if loader.get_output_value('price'):
            if pr:
                yield pr.load_item()
                return

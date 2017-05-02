import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
import hashlib

import csv
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from scrapy import log
from scrapy.shell import inspect_response

from urlparse import urljoin

import itertools
import json
import copy

from product_spiders.spiders.pedalpedal.crcitem import CRCMeta


HERE = os.path.abspath(os.path.dirname(__file__))

class CambriabikeSpider(BaseSpider):
    name = 'cambriabike.com'
    allowed_domains = ['cambriabike.com']
    start_urls = ['http://www.cambriabike.com/']

    def parse(self, response):
        categories = response.xpath('//header[@id="site-header"]//div[@class="navbar-inner"]//a/@href').extract()
        for url in categories:
            if url != "#":
                url = response.urljoin(url)
                yield Request(url, callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        categories = response.xpath('//div[@class="category-cell"]//a/@href').extract()
        # This is a categories page.
        for category in categories:
            yield Request(response.urljoin(category), callback=self.parse_products_list)

        # This is a products list page.
        products = response.xpath('//h2[@class="item-cell-name"]/a/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product)

        # To crawl next page.
        next = response.xpath('//a[@rel="next"]/@href').extract()
        if next:
            yield Request(response.urljoin(next[0]), callback=self.parse_products_list)

    def parse_product(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        identifier = response.xpath('//span[@itemprop="sku"]/text()').extract()
        if identifier:
            identifier = identifier[0]
        else:
            retry = response.meta.get('retry', 1)
            if retry <=3:
                yield Request(response.url, dont_filter=True, callback=self.parse_product, meta={'retry': retry + 1})

        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)

        name = response.xpath('//h1[@itemprop="name"]/text()').extract()
        loader.add_value('name', name[0])
        #price
        price = 0
        price = response.xpath('//span[@class="lead-price"]/text()').extract()
        price = extract_price(price[0]) if price else 0
        loader.add_value('price', price)
        #image_url
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        if image_url:
            image_url = urljoin(response.url, image_url[0])
            loader.add_value('image_url', image_url)
        #brand
        brand = ''
        loader.add_value('brand', brand)
        #category
        categories = response.xpath('//ul[@itemprop="breadcrumb"]/li/a/text()').extract()[1:]
        loader.add_value('category', categories)

        product = loader.load_item()

        url = response.url.split('/')[-1]
        options_url = "http://www.cambriabike.com/api/items?c=4059699&country=GB&currency=USD&fieldset=details&include=facets&language=en&n=2&pricelevel=5&url=" + url
        yield Request(options_url, callback=self.parse_options, meta={'product': product})


    def parse_options(self, response):

        product = response.meta['product']
        j = json.loads(response.body)
        if not j['items']:
            yield product
            return
        fields = [d.get('sourcefrom', '') for d in j['items'][0]['itemoptions_detail']['fields']]
        fields = [d for d in fields if d]
        if not fields:
            yield product
            return
        # process options
        for d in j['items'][0]['matrixchilditems_detail']:  # ##
            item = copy.deepcopy(product)
            item['identifier'] = d['internalid']
            keys = [re.search(r'custitem\d+', k).string for k in d.keys() if re.search(r'custitem\d+', k)]
            if keys:
                item['name'] += ' - ' + ' - '.join([str(d[k]) for k in keys])
            if not item.get('brand', None):
                for facet in j['facets']:
                    if facet['id'] == 'custitem_crc_brand':
                        item['brand'] = facet['values'][0]['label']

            price = extract_price(str(d['onlinecustomerprice_detail']['onlinecustomerprice']))
            item['price'] = price

            if d["showoutofstockmessage"]:
                item['stock'] = 0
            else:
                item['stock'] = 1
            yield item


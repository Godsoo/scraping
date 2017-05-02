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

HERE = os.path.abspath(os.path.dirname(__file__))

class MountainbikesdirectSpider(BaseSpider):
    name = 'mountainbikesdirect.com.au'
    # download_delay = 1
    allowed_domains = ['mountainbikesdirect.com.au']
    start_urls = ['http://www.mountainbikesdirect.com.au/']
    cookie_num = 0
    # brands = []
    id_seen = []

    # Multiple options
    # Out of stock
    # http://www.mountainbikesdirect.com.au/5-10-cyclone-shoe-team-black

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//ul[contains(@class, "navbar-nav")]/li/a/@href').extract()
        categories += hxs.select('//ul[contains(@class, "nav")]/li[position()<6]/ul//li/a/@href').extract()
        for url in categories:  # ##
            # url = urljoin(response.url, link)
            url =  urljoin_rfc(base_url, url)
            self.cookie_num += 1
            yield Request(url, meta={'cookiejar':self.cookie_num}, callback=self.parse_products_list)
        # Miss url
        #return ###
        tmp = hxs.select('//ul[@id="nav"]/li/h2/a[span="Frames"]/@href').extract()
        if tmp:
            self.cookie_num += 1
            yield Request(tmp[0], meta={'cookiejar':self.cookie_num}, callback=self.parse_products_list)


    def parse_products_list(self, response):
        # inspect_response(response, self)
        # return
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//h3[@itemprop="name"]/a/@href').extract():  # ##
            # url = urljoin(response.url, link)
            yield Request(url, meta={'cookiejar': response.meta['cookiejar']}, callback=self.parse_product)

        # To crawl next page.
        #return ###
        tmp = hxs.select('//ul[@class="pagination"]/li/a[i]/@href').extract()
        if tmp:
            yield Request(urljoin_rfc(get_base_url(response), tmp[-1]), meta={'cookiejar': response.meta['cookiejar']}, callback=self.parse_products_list)

    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        tmp = hxs.select('//span[@itemprop="productID"]/text()').extract()
        if tmp:
            loader.add_value('identifier', tmp[0])
        else:
            log.msg('### No product ID at ' + response.url, level=log.INFO)
        tmp = hxs.select('//span[@itemprop="productID"]/text()').extract()
        if tmp:
            loader.add_value('sku', tmp[0])
        name = ''
        tmp = hxs.select('//h1[@itemprop="name"]/text()').extract()
        if tmp:
            name = tmp[0].strip()
            loader.add_value('name', tmp[0].strip())
        else:
            log.msg('### No name at ' + response.url, level=log.INFO)
        # price
        price = 0
        tmp = hxs.select('//div[@class="productpromo"]/text()').extract()
        if not tmp:
            tmp = hxs.select('//div[@itemprop="price"]/text()').extract()
        if tmp:
            price = extract_price("".join(tmp).strip())
            loader.add_value('price', price)
        else:
            loader.add_value('price', 0)
        # image_url
        tmp = hxs.select('//div[@class="zoom"]/img/@src').extract()
        if tmp:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), tmp[0]))

        tmp = hxs.select('//tr[td/strong[text()="Brand"]]/td/text()').extract()
        if tmp:
            loader.add_value('brand', tmp[0])
        # category
        tmp = hxs.select('//ul[@class="breadcrumb"]/li/a/text()').extract()
        if len(tmp):
            tmp = tmp[1:-1]
        for s in tmp:
            loader.add_value('category', s)
        # shipping_cost

        # stock
        in_stock = 'IN STOCK' in ''.join(hxs.select('//div[contains(@class, "wrapper-pricing")]/span/text()').extract()).upper()
        if not in_stock:
            loader.add_value('stock', 0)

       # process options
        options = response.xpath('//div[contains(@class, "visible-lg")]/div[@id="multiitemadd"]/div[@id="buy-child-list"]/table/tbody/tr')

        product = loader.load_item()
        man_num = hxs.select('//div[@class="extra-options"]/ul/li[contains(text(), " Part # ")]/text()').extract()
        if man_num:
            man_num = man_num[0].split(" Part # ")[-1].strip()
            product['metadata'] = {'manufacturer_number': man_num}

        if not options:
            if not product['identifier'] in self.id_seen:
                self.id_seen.append(product['identifier'])
                yield product
            else:
                log.msg('Duplicated product id: ' + product['identifier'], level=log.INFO)
            return

        for option in options:  # ##
            item = copy.deepcopy(product)
            identifier = option.select('td/button[contains(@class, "addtocart")]/@rel').extract()
            if identifier:
                identifier = identifier[0]
            else:
                identifier = option.select('td/input[@class="form-control" and @disabled]/@id').re('\d+')
                if identifier:
                    identifier = identifier[0]
                    item['stock'] = 0
                else:
                    log.msg('No option identifier: ' + response.url, level=log.INFO)
                    continue

            item['identifier'] += '-' + identifier
            option_name = ' '.join(option.select('td/span[@class="listSpecifics"]/span/text()').extract())
            item['name'] += ' - ' + option_name
            image_url = option.select('td/img/@src').extract()
            if image_url:
                item['image_url'] = urljoin_rfc(get_base_url(response), image_url[0])

            price = option.select('td/div[@class="child-price-var"]/text()').extract_first() or option.css('span.productmultilevelprice::text').extract_first()
            price = extract_price(price) if price else '0'
            item['price'] = price

            if not item['identifier'] in self.id_seen:
                self.id_seen.append(item['identifier'])
                yield item
            else:
                log.msg('Duplicated product id: ' + item['identifier'], level=log.INFO)

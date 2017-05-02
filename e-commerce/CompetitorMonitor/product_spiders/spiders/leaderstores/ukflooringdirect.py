# -*- coding: utf-8 -*-
"""
Customer: Leader Stores
Website: http://www.ukflooringdirect.co.uk
Extract all products including options

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4469-leader-stores---new-site---uk-flooring-direct/details#

"""

import os
import re
import json
from copy import deepcopy

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price

from phantomjs import PhantomJS

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from time import sleep


HERE = os.path.abspath(os.path.dirname(__file__))


class UkFlooringDirectSpider(BaseSpider):
    name = 'leaderstores-ukflooringdirect.co.uk'
    allowed_domains = ['ukflooringdirect.co.uk']
    start_urls = ['http://www.ukflooringdirect.co.uk/']

    rotate_agent = True

    def __init__(self, *args, **kwargs):
        super(UkFlooringDirectSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self._browser = PhantomJS.create_browser()

    def spider_closed(self):
        self.log('>> BROWSER => CLOSE')
        self._browser.quit()
        self.log('>> BROWSER => OK')

    def parse(self, response):
        base_url = get_base_url(response)

        categories = response.xpath('//ul[@class="nav"]//a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category))

        products = response.xpath('//div[@class="free-sample-btn-container"]/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        next = response.xpath('//a[@rel="next"]/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]))

    def parse_product(self, response):
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)

        products = []

        name = response.xpath('//h1/text()').extract()
        if not name:
            self.log('>> BROWSER => GET < %s />' % response.url)
            self._browser.get(response.url)
            sleep(5)
            self.log('>> OK')
            response = response.replace(body=self._browser.page_source)

        name = response.xpath('//h1/text()').extract()[0].strip()
        price = response.xpath('//span[@class="wVat big-price"]/text()').extract()
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        categories = response.xpath('//ul[@itemprop="breadcrumb"]/li/a/text()').extract()[1:-1]
        loader.add_value('category', categories)
        brand = response.xpath('//tr[td/strong[contains(text(), "Brand")]]/td/text()').extract()
        brand = brand[-1] if brand else ''
        loader.add_value('brand', brand)
        loader.add_value('shipping_cost', 34.99)
        loader.add_xpath('sku', '//span[@itemprop="sku"]/text()')
        loader.add_xpath('identifier', '//div/@data-itemid')
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])
        product = loader.load_item()
        if not product.get('identifier', None):
            identifier = re.findall('data-itemid="(\d+)"', response.body)
            product['identifier'] = identifier[0]

        if not product.get('sku', None):
            sku = re.findall('"sku">(.*)<', response.body)
            product['sku'] = sku[0]

        options = response.xpath('//select[@data-toggle="select-option"]/option')
        if options:
            for option in options:
                product_option = deepcopy(product)
                option_text = option.xpath('text()').extract()[0].split(' - ')
                name = option_text[0].strip()
                product_option['name'] += ' ' + name
                if len(option_text) > 1:
                    product_option['price'] = extract_price(option_text[-1].strip())
                else:
                    price = response.xpath(
                        '//p[contains(@class, "pricelevels-price")]/span[@class="wVat"]/text()').extract()
                    if price:
                        product_option['price'] = extract_price(price[-1].strip())

                product_option['identifier'] += '-' + option.xpath('@value').extract()[0]
                yield product_option
        else:
            products.append(product)
            price_url = response.xpath('//img[contains(@src, "api/items")]/@src').extract()
            if price_url:
                price_url = urljoin_rfc(base_url, price_url[0])
            else:
                price_url = ('http://www.ukflooringdirect.co.uk/api/items?c=3460739&country=GB&currency=GBP&fieldset='
                             'details&include=facets&language=en&n=2&pricelevel=5&url=')
                product_url = response.url.partition('http://www.ukflooringdirect.co.uk/')[-1]
                price_url = price_url + product_url

            yield Request(price_url, callback=self.parse_price, meta={'item': product})

    def parse_price(self, response):

        item = response.meta['item']

        data = json.loads(response.body)
        price = json.loads(data['items'][0]['custitem_scaretailprice'])['onlinecustomerprice']
        price = round(price * 1.20, 2)
        item['price'] = extract_price(str(price))
        if not item.get('identifier', ''):
            item['identifier'] = data['items'][0]['internalid']
        yield item

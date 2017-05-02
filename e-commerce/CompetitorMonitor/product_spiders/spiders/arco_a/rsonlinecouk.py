# -*- coding: utf-8 -*-

"""
ERF account
RS-Online spider
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5488
"""

import csv
import re
import os

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter

from product_spiders.base_spiders.primary_spider import PrimarySpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class RsOnlineSpider(PrimarySpider):
    name = 'arco-a-rs-online.com'
    allowed_domains = ['rs-online.com']
    errors = []

    csv_file = 'rsonline_crawl.csv'

    def __init__(self, *args, **kwargs):
        super(RsOnlineSpider, self).__init__(*args, **kwargs)
        self.prods_count = 0

        self.codes = {}
        self._current_identifiers = []

        with open(os.path.join(HERE, 'competitors_codes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.codes[row['url'].lower()] = row['code']

    def start_requests(self):
        yield Request('http://uk.rs-online.com/web/', callback=self.parse_full)

    def parse_full(self, response):
        if 'error.xhtml' in response.url:
            retry_no = int(response.meta.get('retry_no', 0))
            if retry_no < 10:
                for url in response.meta['redirect_urls']:
                    meta = response.meta.copy()
                    meta['retry_no'] = retry_no + 1
                    yield Request(url, dont_filter=True, meta=meta, callback=self.parse_full)
                return

        hxs = HtmlXPathSelector(response)

        cats = hxs.select('//li[@class="allProducts"]//a/@href').extract()
        for cat in cats:
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse_subcats_full)

    def parse_subcats_full(self, response):
        if 'error.xhtml' in response.url:
            retry_no = int(response.meta.get('retry_no', 0))
            if retry_no < 10:
                for url in response.meta['redirect_urls']:
                    meta = response.meta.copy()
                    meta['retry_no'] = retry_no + 1
                    yield Request(url, dont_filter=True, meta=meta, callback=self.parse_subcats_full)
                return

        hxs = HtmlXPathSelector(response)

        subcats = hxs.select('//div[@id="categories"]//a/@href').extract()
        for cat in subcats:
            url = urljoin_rfc(get_base_url(response), cat)
            if (not '?' in url) and (not url.endswith('/')):
                url += '/'
            url = add_or_replace_parameter(url, 'sort-by', 'P_manufacturerPartNumber')
            url = add_or_replace_parameter(url, 'sort-order', 'asc')
            url = add_or_replace_parameter(url, 'view-type', 'List')
            url = add_or_replace_parameter(url, 'sort-option', 'Manufacturers+Part+Number')
            yield Request(url, callback=self.parse_subcats_full)

        pages = hxs.select('//div[@class="checkoutPaginationContent"]//noscript/a/@href').extract()
        for url in pages:
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_subcats_full)

        for product in self.parse_product_list(response):
            yield product

    def parse_product_list(self, response):
        if 'error.xhtml' in response.url:
            retry_no = int(response.meta.get('retry_no', 0))
            if retry_no < 10:
                for url in response.meta['redirect_urls']:
                    meta = response.meta.copy()
                    meta['retry_no'] = retry_no + 1
                    yield Request(url, dont_filter=True, meta=meta, callback=self.parse_product_list)
                return

        hxs = HtmlXPathSelector(response)

        products = hxs.select('//div[@id="mainContent"]//tr[@class="resultRow"]')

        for product in products:
            product_name = product.select('.//a/img//@title').extract()
            if not product_name:
                retries = response.meta.get('retries', 0)
                if retries < 3:
                    meta=response.meta.copy()
                    meta['retries'] = retries + 1
                    yield response.request.replace(dont_filter=True, meta=meta)
                    return
                else:
                    self.errors.append("No name in list on " + response.url)
                    continue
            product_name = product_name.pop()
            url = product.select('.//a/img/../@href').extract()
            url = urljoin_rfc(get_base_url(response), url[0])
            brand = product.select('.//li/span[contains(@class, "labelText") and contains(text(), "Brand")]/following-sibling::a/text()').extract()
            if brand:
                brand = brand[0].strip()
            else:
                brand = ""
            price = product.select('.//span[contains(@class, "price")]/text()').extract()
            if not price:
                retries = response.meta.get('retries', 0)
                if retries < 3:
                    meta=response.meta.copy()
                    meta['retries'] = retries + 1
                    yield response.request.replace(dont_filter=True, meta=meta)
                    return
                else:
                    self.errors.append('No price for %s on %s' % (product_name, response.url))
                    continue
            price = price.pop()
            category = hxs.select('//div[@class="breadCrumb"]//li/a/text()').extract()[-1].strip()
            identifier = product.select('.//a[@class="primarySearchLink"]/text()').extract()
            image_url = product.select('.//a/img/@src').extract()

            brand_in_name = False
            for w in re.findall('([a-zA-Z]+)', product_name):
                if w.upper() in brand.upper():
                    brand_in_name = True

            if brand.upper() not in product_name.upper() and not brand_in_name:
                product_name = brand + ' ' + product_name

            loader = ProductLoader(selector=hxs, item=Product())
            loader.add_value('name', product_name)
            loader.add_value('url', url)
            loader.add_value('brand', brand)
            loader.add_value('price', price)
            loader.add_value('category', category)
            loader.add_value('sku', identifier)
            loader.add_value('image_url', image_url)
            loader.add_value('identifier', identifier)

            product = loader.load_item()

            if product.get('identifier'):
                if product['identifier'] not in self._current_identifiers:
                    self._current_identifiers.append(product['identifier'])
                    yield product

                    '''
                    yield Request(product['url'], callback=self.parse_product, meta={'item':product})
                    '''

            self.prods_count += 1

    def parse_product(self, response):
        if 'error.xhtml' in response.url:
            retry_no = int(response.meta.get('retry_no', 0))
            if retry_no < 10:
                for url in response.meta['redirect_urls']:
                    meta = response.meta.copy()
                    meta['retry_no'] = retry_no + 1
                    yield Request(url, dont_filter=True, meta=meta, callback=self.parse_product)
                return

        hxs = HtmlXPathSelector(response)
        product = response.meta['item']

        if hxs.select('//div[contains(@class,"notStockMessage")]'):
            product['stock'] = 0
        else:
            product['stock'] = 1

        yield product

    # Only if Proxy Service enabled
    def proxy_service_check_response(self, response):
        return ('error.xhtml' in response.url)

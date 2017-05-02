# -*- coding: utf-8 -*-


"""
- Original assembla ticket #: 3916
- Run Scrapy >= 0.15 for correct operation (cookiejar feature)
- Prices including Tax
- It uses cache by using previous crawl data and updating only prices and stock status from product lists.
  Enter to product page only for new products, this is only for some fields like SKU which
  are not in products list page
"""


__author__ = 'Emiliano M. Rudenick (emr.frei@gmail.com)'


import os
import re
import json
import pandas as pd
from decimal import Decimal
from product_spiders.base_spiders.primary_spider import PrimarySpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from scrapy.utils.response import get_base_url
from product_spiders.config import DATA_DIR
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)


class LawsonHisSpider(PrimarySpider):
    name = 'ffxtools-lawson-his.co.uk'
    allowed_domains = ['lawson-his.co.uk']
    start_urls = ['http://www.lawson-his.co.uk/categories']

    csv_file = 'lawson-his.co.uk_products.csv'

    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; rv:33.0) Gecko/20100101 Firefox/33.0'

    def __init__(self, *args, **kwargs):
        super(LawsonHisSpider, self).__init__(*args, **kwargs)

        self._current_cookie = 0
        self.products_cache_filename = ''
        self.products_cache = None
        self._identifiers = set()

    def start_requests(self):
        if hasattr(self, 'prev_crawl_id'):
            self.products_cache_filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
            self.products_cache = pd.read_csv(self.products_cache_filename, dtype=pd.np.str)
            self.products_cache = self.products_cache.where(pd.notnull(self.products_cache), None)
            self.products_cache['viewed'] = False

        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[@class="catblocks"]//a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

        if not categories:
            new_url = add_or_replace_parameter(response.url, 'limit', '25')
            new_url = add_or_replace_parameter(new_url, 'mode', 'list')
            self._current_cookie += 1
            yield Request(new_url,
                          dont_filter=True,
                          callback=self.parse_list,
                          meta={'cookiejar': self._current_cookie})

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        products = hxs.select('//*[@id="products-list"]//*[contains(@class, "item")]')
        for product_xs in products:
            product_cached_found = False
            product_price = product_xs.select('.//*[contains(@id, "price-including-tax-")]/text()').re(r'[\d,.]+')
            product_url = product_xs.select('.//*[contains(@class, "product-primary")]//*[contains(@class, "product-name")]//a/@href').extract()
            product_identifier = product_xs.select('.//*[contains(@id, "price-including-tax-")]/@id').re(r'price-including-tax-(\d+)')
            out_stock = bool(product_xs.select('.//*[contains(@class, "availability") and contains(@class, "out-of-stock")]'))
            options_found = bool(product_xs.select('.//*[contains(@class, "button") and contains(text(), "View Details")]'))
            if (not options_found) and product_identifier and product_price and (self.products_cache is not None):
                cached_item = self.products_cache[self.products_cache['identifier'] == product_identifier[0]]
                if not cached_item.empty:
                    product_cached_found = True
                    cached_item_dict = dict(cached_item.iloc[0])
                    del cached_item_dict['viewed']
                    cached_product = Product(cached_item_dict)
                    cached_product['price'] = Decimal(product_price[0].replace(',', ''))
                    del cached_product['dealer']
                    if cached_product['name'] is None:
                        del cached_product['name']
                    if cached_product['category'] is None:
                        del cached_product['category']
                    if cached_product['shipping_cost']:
                        cached_product['shipping_cost'] = Decimal(cached_product['shipping_cost'].replace(',', ''))
                    else:
                        del cached_product['shipping_cost']
                    if out_stock:
                        cached_product['stock'] = 0
                    else:
                        del cached_product['stock']
                    self.products_cache['viewed'].loc[cached_item.index] = True

                    if cached_product['identifier'] not in self._identifiers:
                        self._identifiers.add(cached_product['identifier'])
                        yield cached_product

            if not product_cached_found:
                yield Request(urljoin_rfc(base_url, product_url[0]),
                              callback=self.parse_product,
                              meta=response.meta)

        pages = map(lambda u: urljoin_rfc(base_url, u), set(hxs.select('//*[@class="pages"]//a/@href').extract()))
        for url in pages:
            yield Request(url, callback=self.parse_list, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_identifier = hxs.select('//input[@name="product"]/@value').extract()
        product_name = hxs.select('//meta[@property="og:title"]/@content').extract()
        product_price = hxs.select('//meta[@property="og:price:amount"]/@content').extract()
        product_image = hxs.select('//meta[@property="og:image"]/@content').extract()
        product_brand = hxs.select('//meta[@property="og:brand"]/@content').extract()
        product_in_stock = 'instock' in hxs.select('//meta[@property="og:availability"]/@content').extract()
        product_sku = hxs.select('//meta[@property="og:gtin"]/@content').extract()
        product_category = map(unicode.strip, hxs.select('//div[@class="breadcrumbs"]//li/a/text()|'
                                                         '//div[@class="breadcrumbs"]//li/strong/text()')\
                               .extract())[1:-1]

        options_config = re.search(r'var spConfig=new Product.Config\((.*)\)', response.body)
        if not options_config:
            options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)

        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            prices = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))
                        prices[product] = prices.get(product, 0) +  float(option['price'])

            for option_identifier, option_name in products.iteritems():
                l = ProductLoader(item=Product(), response=response)
                l.add_value('name', product_name[0] + ' ' + option_name.strip())
                if product_sku:
                    l.add_value('sku', product_sku)
                l.add_value('price', Decimal(product_price[0].replace(',', '')) + Decimal(prices[option_identifier]))
                l.add_value('identifier', option_identifier)
                if product_brand:
                    l.add_value('brand', product_brand)
                l.add_value('category', product_category)
                if product_image:
                    l.add_value('image_url', urljoin_rfc(base_url, product_image[0]))
                l.add_value('url', response.url)
                if not product_in_stock:
                    l.add_value('stock', 0)

                product_item = l.load_item()
                if ('price' in product_item) and product_item['price'] and product_item['price'] > Decimal('100'):
                    product_item['shipping_cost'] = Decimal('4.98')

                if product_item['identifier'] not in self._identifiers:
                    self._identifiers.add(product_item['identifier'])
                    yield product_item


        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', product_identifier)
        l.add_value('name', product_name)
        l.add_value('price', product_price)
        l.add_value('url', response.url)
        l.add_value('category', product_category)
        if product_image:
            l.add_value('image_url', urljoin_rfc(base_url, product_image[0]))
        if product_brand:
            l.add_value('brand', product_brand)
        if product_sku:
            l.add_value('sku', product_sku)
        if not product_in_stock:
            l.add_value('stock', 0)

        product_item = l.load_item()
        if ('price' in product_item) and product_item['price'] and product_item['price'] > Decimal('100'):
            product_item['shipping_cost'] = Decimal('4.98')

        if product_item['identifier'] not in self._identifiers:
            self._identifiers.add(product_item['identifier'])
            yield product_item

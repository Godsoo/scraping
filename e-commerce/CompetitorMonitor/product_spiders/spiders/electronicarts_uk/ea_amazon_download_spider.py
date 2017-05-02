# -*- coding: utf-8 -*-
import os
import re
import csv
from copy import deepcopy
from urlparse import urljoin

from scrapy import log

from product_spiders.items import Product

from urlparse import urlparse
from urlparse import urljoin as urljoin_rfc
from urlparse import parse_qs

from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url

#from product_spiders.base_spiders.amazonspider import BaseAmazonSpider, filter_name

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider

from product_spiders.base_spiders.legoamazon import (
    check_price_valid,
)

HERE = os.path.abspath(os.path.dirname(__file__))

from scrapy import log

class EAAmazonSpider(BaseAmazonSpider):
    name = 'electronicarts-uk-amazon.co-uk-download'
    all_sellers = False

    collect_products_from_list = False

    _use_amazon_identifier = True

    do_retry = True
    max_retry_count = 5

    domain = 'amazon.co.uk'

    amazon_direct = True

    collect_reviews = False
    reviews_once_per_product_without_dealer = False

    user_agent = 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36'

    def start_requests(self):
        with open(os.path.join(HERE, 'EAMatches.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Amazon - PC Download']!="No match":
                    s_item = {
                            'sku': row['sku'],
                            'brand': '',
                            'name': '',
                            'category': '',
                            'price': 0,
                            }
                    yield Request(row['Amazon - PC Download'], meta={'search_string': '', 'search_item': s_item}, dont_filter=True, callback=self.parse_product)


    def match(self, meta, search_item, found_item):
        return True

    def parse_product(self, response):
        """
        Parse product just to get seller name
        """
        self.current_search_item = response.meta['search_item']

        if self.scraper.antibot_protection_raised(response.body):
            if self.do_retry:
                yield self.retry_download(url=response.url,
                                          metadata=response.meta,
                                          callback=self.parse_product_list)
            else:
                self.log('WARNING: Amazon antibot protection detected, consider using proxy/tor, url: [{}]'.format(
                    response.url))

        product_info = self.scraper.scrape_product_details_page(response)

        product_info['sku'] = response.meta['search_item']['sku']
        if not product_info:
            self.log("WARNING: no product info: %s" % response.url)
            return

        if response.meta.get('seller_identifier', None) and not product_info.get('seller_identifier', None):
            product_info['seller_identifier'] = response.meta['seller_identifier']

        check_match = response.meta.get('check_match', True)

        if check_match and not self.match(response.meta, self.current_search_item, product_info):
            return

        hxs = HtmlXPathSelector(response)

        if self.parse_options:
            if product_info['options'] and response.meta.get('parse_options', True):
                self.log('>>>> OPTIONS FOUND => %s' % response.url)

                for option in product_info['options']:
                    new_meta = response.meta.copy()
                    new_meta.update({
                        'parse_options': False,
                        'search_string': self.current_search,
                        'search_item': self.current_search_item,
                        'check_match': check_match
                    })
                    yield Request(
                        option['url'],
                        self.parse_product,
                        meta=new_meta
                    )
                return
            else:
                if product_info['option_texts']:
                    product_info['name'] += ' [' + ', '.join(product_info['option_texts']) + ']'

        # Amazon Direct
        if self.amazon_direct:
            if self.collect_reviews and product_info.get('reviews_url'):
                new_meta = response.meta.copy()
                new_meta.update({
                    'search_string': response.meta['search_string'],
                    'search_item': self.current_search_item,
                    'found_item': product_info
                })
                yield Request(
                    product_info['reviews_url'],
                    callback=self.parse_reviews,
                    meta=new_meta
                )
            else:
                out_of_stock = hxs.select('//div[@class="availRed"]').extract()
                if out_of_stock:
                    product_info['stock'] = '0'
                product = self.construct_product(product_info)
                self._collect_amazon_direct(product, response.meta)
        # Buy Box
        elif self.only_buybox:
            if (product_info['vendor'] and self._seller_ok(product_info['vendor'])) or \
                    self.collect_products_with_no_dealer:
                if self.collect_reviews and product_info.get('reviews_url'):
                    new_meta = response.meta.copy()
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': self.current_search_item,
                        'found_item': product_info
                    })
                    yield Request(
                        product_info['reviews_url'],
                        callback=self.parse_reviews,
                        meta=new_meta
                    )
                else:
                    product = self.construct_product(product_info)
                    self._collect_buybox(product, response.meta)
        # all sellers / lowest price
        elif self.all_sellers or self.lowest_product_and_seller:
            # Go to MBC lists to get dealers prices
            collect_mbc = response.meta.get('collect_mbc', True)
            if collect_mbc and product_info.get('mbc_list_url_new') and self.collect_new_products:
                # yield mbc parse
                new_meta = response.meta.copy()
                new_meta.update({
                    'search_string': response.meta.get('search_string'),
                    'search_item': self.current_search_item,
                    'found_item': product_info
                })
                yield Request(
                    product_info['mbc_list_url_new'],
                    callback=self.parse_mbc_list,
                    meta=new_meta
                )
            elif collect_mbc and product_info.get('mbc_list_url_used') and self.collect_used_products:
                # yield mbc parse
                new_meta = response.meta.copy()
                new_meta.update({
                    'search_string': response.meta.get('search_string'),
                    'search_item': self.current_search_item,
                    'found_item': product_info
                })
                yield Request(
                    product_info['mbc_list_url_used'],
                    callback=self.parse_mbc_list,
                    meta=new_meta
                )
            else:
                if (product_info['vendor'] and self._seller_ok(product_info['vendor'])) or \
                        self.collect_products_with_no_dealer:
                    if self.collect_reviews and product_info.get('reviews_url'):
                        new_meta = response.meta.copy()
                        new_meta.update({
                            'search_string': response.meta.get('search_string'),
                            'search_item': self.current_search_item,
                            'found_item': product_info
                        })
                        yield Request(
                            product_info['reviews_url'],
                            callback=self.parse_reviews,
                            meta=new_meta
                        )
                    else:
                        product = self.construct_product(product_info)
                        self.log("[[TESTING]] collect parse product: %s" % product['identifier'])
                        self._collect(product)

# -*- coding: utf-8 -*-
import os
import re
import csv
import xlrd
from copy import deepcopy
from urlparse import urljoin

from product_spiders.items import Product

from urlparse import urlparse
from urlparse import urljoin as urljoin_rfc
from urlparse import parse_qs

from scrapy import log

from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url

# from product_spiders.base_spiders.amazonspider import BaseAmazonSpider, filter_name

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider
from product_spiders.base_spiders.amazonspider2.scraper import AmazonScraper, AmazonUrlCreator

from product_spiders.base_spiders.legoamazon import (
    check_price_valid,
)

HERE = os.path.abspath(os.path.dirname(__file__))

from scrapy import log

class LogitechAmazonSpider(BaseAmazonSpider):
    name = 'logitech-amazon.de-buybox'

    collect_products_from_list = False
    model_as_sku = True

    _use_amazon_identifier = True

    only_buybox = True

    do_retry = True
    domain = 'amazon.de'

    ean_list = {}

    collect_reviews = True
    reviews_once_per_product_without_dealer = False

    user_agent = 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36'

    map_products_csv = os.path.join(HERE, 'logitech_map_products.csv')
    map_price_field = 'map'
    map_join_on = [('sku', 'mpn'), ('sku', 'ean13')]

    def get_search_query_generator(self):

        file_path = HERE + '/logitech_de.xlsx'
        wb = xlrd.open_workbook(file_path)
        sh = wb.sheet_by_name('Sheet1')

        for rownum in xrange(sh.nrows):
            if rownum < 2:
                continue
            row = sh.row_values(rownum)

            self.ean_list[row[4]] = row[5]

            s_item = {
                    'sku': '',
                    'brand': row[2],
                    'name': '',
                    'category': '',
                    'price': 0,
                    }
            yield ('"%s"' % row[4], s_item)

    def match(self, meta, search_item, found_item):
        search_item_brand = search_item['brand'].upper() if search_item.get('brand', '') else ''
        found_item_brand = found_item['brand'].upper() if found_item.get('brand', '') else ''
        if search_item_brand in found_item.get('name', '').upper() or search_item_brand in found_item_brand:
            return True

    def __parse_product(self, response):
        """
        Parse product just to get seller name
        """
        if self.scraper.antibot_protection_raised(response.body_as_unicode()):
            if self.do_retry:
                yield self.retry_download(url=response.url,
                                          metadata=response.meta,
                                          callback=self.parse_product)
            else:
                self.log('[AMAZON] WARNING: Amazon antibot protection detected, consider using proxy/tor, url: [{}]'.format(
                    response.url))

        product_info = self.scraper.scrape_product_details_page(response)
        if not product_info:
            self.log("[AMAZON] WARNING: no product info: %s" % response.url)
            return
        # Fix self.current_search_item and meta['search_item']. Needed for BSM spider

        hxs = HtmlXPathSelector(response)

        out_of_stock = hxs.select('//div[@class="availRed"]').extract()
        not_available = hxs.select('//span[@class="availOrange"]').extract()
        if out_of_stock or not_available:
            product_info['stock'] = '0'

        sku = hxs.select('//tr[td[text()="Modellnummer"]]/td[@class="value"]/text()').extract()
        if sku:
            product_info['sku'] = sku[0]
        else:
            product_info['sku'] = ''.join(hxs.select('//li[b/text()="Modellnummer:"]/text()').extract()).strip()
            if not product_info['sku']:
                product_info['sku'] = ''.join(hxs.select('//li[contains(b/text(), "Herstellerreferenz")]/text()').extract()).strip()
                if not product_info['sku']:
                    product_info['sku'] = ''.join(hxs.select('//tr[contains(td/text(), "Herstellerreferenz")]/td[@class="value"]/text()').extract()).strip()


        if not product_info['price']:
            product_info['price'] = ''.join(hxs.select('//td/b[@class="priceLarge"]/text()').extract())
            if not product_info['price']:
                product_info['price'] = ''.join(hxs.select('//span[@id="priceblock_ourprice"]/text()').extract())

            product_info['dealer'] = ''.join(hxs.select('//div[@class="buying"]/b/a[contains(@href, "seller")]/text()').extract())
            if not product_info['dealer']:
                product_info['dealer'] = ''.join(hxs.select('//div[@id="merchant-info"]/a[contains(@href, "seller")]/text()').extract())


        if not response.meta.get('search_item'):
            response.meta['search_item'] = product_info
        if not self.current_search_item:
            self.current_search_item = product_info

        if response.meta.get('seller_identifier', None) and not product_info.get('seller_identifier', None):
            product_info['seller_identifier'] = response.meta['seller_identifier']

        check_match = response.meta.get('check_match', True)

        if self.type == 'search':
            match = self.match(response.meta, self.current_search_item, product_info)
        elif self.type == 'category':
            match = True
        elif self.type == 'asins':
            match = True
        else:
            raise CloseSpider("Wrong spider type: %s" % self.type)

        if check_match and not match:
            self.log("[AMAZON] WARNING: product does not match: %s" % response.url)
            return

        if self.parse_options:
            if product_info['options'] and response.meta.get('parse_options', True):
                self.log('[AMAZON] OPTIONS FOUND => %s' % response.url)

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

        if self.type == 'asins':
            url_asin = AmazonUrlCreator.get_product_asin_from_url(product_info['url'])
            if product_info['asin'].lower() != url_asin.lower():
                self.log("[AMAZON] product ASIN '%s' does not match url ASIN '%s'. Page: %s" %
                         (product_info['asin'], url_asin, response.url))
                return

        # Amazon Direct
        if self.amazon_direct:
            if self.collect_reviews and product_info.get('reviews_url'):
                new_meta = response.meta.copy()
                new_meta['found_item'] = product_info
                if self.type == 'search':
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': self.current_search_item,
                    })
                yield Request(
                    product_info['reviews_url'],
                    callback=self.parse_reviews,
                    meta=new_meta
                )
            else:
                product = self.construct_product(product_info, meta=response.meta)
                self.log("[AMAZON] collect parse product: %s" % product['identifier'])
                if self.type == 'category':
                    yield product
                else:
                    self._collect_amazon_direct(product, response.meta)
        # Buy Box
        elif self.only_buybox:
            if (product_info['vendor'] and self._seller_ok(product_info['vendor'])) or \
                    self.collect_products_with_no_dealer:
                if self.collect_reviews and product_info.get('reviews_url'):
                    new_meta = response.meta.copy()
                    new_meta['found_item'] = product_info
                    if self.type == 'search':
                        new_meta.update({
                            'search_string': response.meta['search_string'],
                            'search_item': self.current_search_item,
                        })
                    yield Request(
                        product_info['reviews_url'],
                        callback=self.parse_reviews,
                        meta=new_meta
                    )
                else:
                    product = self.construct_product(product_info, meta=response.meta)
                    self.log("[AMAZON] collect parse product: %s" % product['identifier'])
                    if self.type == 'category':
                        yield product
                    else:
                        self._collect_buybox(product, response.meta)
            elif not product_info['vendor']:
                # TODO: collect vendor from vendor details page
                self.log("[AMAZON] WARNING: product with no vendor: %s" % response.url)
            else:
                self.log("[AMAZON] WARNING: vendor not allowed: %s" % response.url)
        # all sellers / lowest price
        elif self.all_sellers or self.lowest_product_and_seller:
            # Go to MBC lists to get dealers prices
            collect_mbc = response.meta.get('collect_mbc', True)
            if collect_mbc and product_info.get('mbc_list_url_new') and self.collect_new_products:
                # yield mbc parse
                new_meta = response.meta.copy()
                new_meta['found_item'] = product_info
                if self.type == 'search':
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': self.current_search_item,
                    })
                yield Request(
                    product_info['mbc_list_url_new'],
                    callback=self.parse_mbc_list,
                    meta=new_meta
                )
            elif collect_mbc and product_info.get('mbc_list_url_used') and self.collect_used_products:
                # yield mbc parse
                new_meta = response.meta.copy()
                new_meta['found_item'] = product_info
                if self.type == 'search':
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': self.current_search_item,
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
                        new_meta['found_item'] = product_info
                        if self.type == 'search':
                            new_meta.update({
                                'search_string': response.meta['search_string'],
                                'search_item': self.current_search_item,
                            })
                        yield Request(
                            product_info['reviews_url'],
                            callback=self.parse_reviews,
                            meta=new_meta
                        )
                    else:
                        product = self.construct_product(product_info, meta=response.meta)
                        self.log("[AMAZON] collect parse product: %s" % product['identifier'])
                        if self.type == 'category':
                            yield product
                        else:
                            self._collect(product)
                elif not product_info['vendor']:
                    # TODO: collect vendor from vendor details page
                    self.log("[AMAZON] WARNING: product with no vendor: %s" % response.url)
                else:
                    self.log("[AMAZON] WARNING: vendor not allowed: %s" % response.url)


    def __parse_product_list(self, response):
        """
        This function is callback for Scrapy. It processes search results page

        TODO: incorporate cache
        """
        if self.scraper.antibot_protection_raised(response.body_as_unicode()):
            if self.do_retry:
                yield self.retry_download(url=response.url,
                                          metadata=response.meta,
                                          callback=self.parse_product_list)
            else:
                self.log('[AMAZON] WARNING: Amazon antibot protection detected, consider using proxy/tor, url: %s' %
                         response.url)

        follow_suggestions = response.meta.get("follow_suggestions", True)
        is_main_search = response.meta.get("is_main_search", True)

        data = self.scraper.scrape_search_results_page(response)

        if not self.check_number_of_results_fits(data):
            requests = self.get_subrequests_for_search_results(response, data)
            self.log("[AMAZON] WARNING: Number of results is too big (%d). Splitting to %d requests. URL: %s" %
                     (data['results_count'], len(requests), response.url))
            for req in requests:
                yield req
            return

        if data['products']:
            items = data['products']
            found_for = None
            if self.type == 'search':
                found_for = self.current_search
            elif self.type == 'category':
                found_for = self.current_category
            self.log('[AMAZON] Found products for [%s]' % found_for)

        elif data['suggested_products'] and self.try_suggested:
            items = data['suggested_products']
            self.log('[AMAZON] No products found for [%s]. Using suggested products. URL: %s' %
                     (self.current_search, response.url))
        else:
            items = []

        if not items and not response.meta.get('ean_search', False):
            search_string = self.ean_list[self.current_search.replace('"', '')]
            url = AmazonUrlCreator.build_search_url(self.domain, search_string, self.amazon_direct)

            s_item = {
                    'sku': '',
                    'brand': '',
                    'name': '',
                    'category': '',
                    'price': 0,
                    }

            yield Request(url, meta={'search_string': search_string, 'search_item': s_item, 'ean_search':True},
                        dont_filter=True, callback=self.parse_product_list)

        if not data['products'] and follow_suggestions and self.try_suggested:
            self.log('[AMAZON] No products or suggested products found for [%s], trying suggested searches' % self.current_search)
            for url in data['suggested_search_urls']:
                # yield request, should mark that it's referred as suggested search and as so do not check other suggestions
                new_meta = response.meta.copy()
                new_meta.update({
                    'search_string': response.meta['search_string'],
                    'search_item': self.current_search_item,
                    'follow_suggestions': False,
                    'is_main_search': False,
                })
                yield Request(
                    url,
                    meta=new_meta,
                    dont_filter=True,
                    callback=self.parse_product_list
                )

        matched_any = False

        # Amazon Direct
        if self.amazon_direct and not self.only_buybox and not self.all_sellers and not self.lowest_product_and_seller:
            for item in items:
                results = list(self._process_product_list_item_amazon_direct(response, item))
                matched_any = results[-1]
                for req in results[:-1]:
                    yield req
        # Buy-Box
        elif self.only_buybox and not self.amazon_direct and not self.all_sellers and not self.lowest_product_and_seller:
            for item in items:
                results = list(self._process_product_list_item_buybox(response, item))
                matched_any = results[-1]
                for req in results[:-1]:
                    yield req
        # All sellers / lowest price dealer
        elif self.all_sellers or self.lowest_product_and_seller:
            for item in items:
                results = list(self._process_product_list_item_all_sellers(response, item))
                matched_any = results[-1]
                for req in results[:-1]:
                    yield req

        next_url = data['next_url']

        follow_next = False
        if self.type == 'category':
            follow_next = True
        elif self.type == 'search':
            # Follow to next pages only for original search
            # and suggested search if at least one product matched from first page
            # otherwise it tries to crawl the whole Amazon or something like that
            follow_next = (is_main_search or matched_any)
        if next_url and follow_next:
            page = data.get('current_page', 1)
            page = int(page) if page is not None else 1
            if self.max_pages is None or page <= self.max_pages:
                new_meta = response.meta.copy()
                new_meta.update({
                    'follow_suggestions': False,
                    'is_main_search': is_main_search,
                    'current_page': page + 1
                })
                yield Request(
                    next_url,
                    meta=new_meta,
                    dont_filter=True,
                    callback=self.parse_product_list
                )
            else:
                self.log('[AMAZON] Max page limit %d reached. URL: %s' % (self.max_pages, response.url))
        elif next_url:
            self.log('[AMAZON] Not following next page from %s: %s' % (response.url, next_url))
        else:
            self.log('[AMAZON] No next url from %s' % response.url)

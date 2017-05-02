# -*- coding: utf-8 -*-
import csv
import os

from scrapy import log
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider

HERE = os.path.abspath(os.path.dirname(__file__))

class AmazonSpiderDirect(BaseAmazonSpider):
    name = 'na1-toymonitor'
    domain = 'www.amazon.co.uk'

    type = 'category'
    model_as_sku = True
    _use_amazon_identifier = True
    amazon_direct = False
    sellers = []
    exclude_sellers = []
    only_buybox = True
    collect_products_with_no_dealer = False
    do_retry = True
    parse_options = True
    max_retry_count = 50
    _max_pages = 200

    try_suggested = False

    def get_category_url_generator(self):
        urls = []
        with open(os.path.join(HERE, 'toymonitor.csv')) as f:
            urls = list(csv.reader(f))

        for url, name in urls:
            yield (url, name)

    def parse_product(self, response):
        """
        Parse product just to get seller name
        """
        if self.scraper.antibot_protection_raised(response.body_as_unicode()):
            self.antibot_blocked_count += 1
            if self.should_do_retry(response):
                self.log('[AMAZON] WARNING: Amazon antibot protection detected when crawling url: %s' %
                         response.url)
                yield self.retry_download(url=response.url,
                                          metadata=response.meta,
                                          callback=self.parse_product)
            else:
                self.antibot_blocked_fully_urls.add(response.url)
                self.log('[AMAZON] WARNING: Amazon antibot protection detected, consider using proxy/tor, url: %s' %
                         response.url)
            return

        self.parsed_count['parse_product'] += 1

        try:
            product_info = self.scraper.scrape_product_details_page(response, self.options_only_color)
        except AmazonScraperProductDetailsException:
            if self.should_do_retry(response):
                self.log('[AMAZON] WARNING: Could not parse product details page: %s' % response.url)
                yield self.retry_download(url=response.url,
                                          metadata=response.meta,
                                          callback=self.parse_product)
            else:
                self.log('[AMAZON] ERROR: Could not parse product details page: %s' % response.url)
                self.errors.append('Could not parse product details page: %s' % response.url)
            return
        if not product_info:
            self.log("[AMAZON] WARNING: no product info: %s" % response.url)
            return
        # Fix self.current_search_item and meta['search_item']. Needed for BSM spider
        if not response.meta.get('search_item'):
            response.meta['search_item'] = product_info
        if not self.current_search_item:
            self.current_search_item = response.meta['search_item']

        # If no price found and ajax price url is present - collect price from ajax
        if not product_info['price'] and product_info['ajax_price_url']:
            new_meta = response.meta.copy()
            new_meta['product_info'] = product_info
            yield Request(
                product_info['ajax_price_url'],
                callback=self.parse_ajax_price,
                dont_filter=True,
                meta=new_meta
            )
            return
        for res in self._process_product_info_product_details(response, product_info):
            yield res

    def _process_product_info_product_details(self, response, product_info):
        """
        This needs to be in separate function because used by two methods: parse_product_details and parse_ajax_price
        """
        if response.meta.get('seller_identifier', None) and not product_info.get('seller_identifier', None):
            product_info['seller_identifier'] = response.meta['seller_identifier']

        check_match = response.meta.get('check_match', True)

        match = self.match(response.meta, self.current_search_item, product_info)

        if check_match and not match:
            self.log("[AMAZON] WARNING: product does not match: %s" % response.url)
            return

        self.log('Fulfilled by: {}'.format(product_info.get('fulfilled_by')))
        self.log('Vendor: {}'.format(product_info.get('vendor')))

        fulfilled_by = product_info.get('fulfilled_by')
        vendor = product_info.get('vendor')
        if not vendor or (vendor and vendor.lower().strip() != 'amazon'):
            if not fulfilled_by or (fulfilled_by and fulfilled_by.lower().strip() != 'amazon'):
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
                        meta=new_meta,
                        dont_filter=True
                    )
                return
            else:
                if product_info['name_with_options']:
                    product_info['name'] = product_info['name_with_options']
                elif product_info['option_texts']:
                    product_info['name'] += ' [' + ', '.join(product_info['option_texts']) + ']'

        if self.type == 'asins':
            url_asin = AmazonUrlCreator.get_product_asin_from_url(product_info['url'])
            if product_info['asin'].lower() != url_asin.lower():
                self.log("[AMAZON] product ASIN '%s' does not match url ASIN '%s'. Page: %s" %
                         (product_info['asin'], url_asin, response.url))
                return

        # Amazon Direct
        if self.amazon_direct:
            if self.collect_reviews and product_info.get('reviews_url') and response.meta.get('collect_reviews', True):
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
                if self.collect_reviews and product_info.get('reviews_url') and response.meta.get('collect_reviews', True):
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
                    if self.collect_reviews and product_info.get('reviews_url') and response.meta.get('collect_reviews', True):
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
                        use_seller_id_in_identifier = False \
                            if self.lowest_product_and_seller and not self.lowest_seller_collect_dealer_identifier else True
                        product = self.construct_product(product_info, meta=response.meta,
                                                         use_seller_id_in_identifier=use_seller_id_in_identifier)
                        self.log("[AMAZON] collect parse product: %s" % product['identifier'])
                        if self.type == 'category':
                            yield product
                        else:
                            self._collect(product)
                elif not product_info['vendor']:
                    # TODO: collect vendor from vendor details page
                    if not product_info['unavailable']:
                        self.log("[AMAZON] WARNING: Could not scrape vendor from product details: %s" % response.url)
                        self.errors.append("Could not scrape vendor from product details: %s" % response.url)
                else:
                    self.log("[AMAZON] WARNING: vendor not allowed: %s" % response.url)

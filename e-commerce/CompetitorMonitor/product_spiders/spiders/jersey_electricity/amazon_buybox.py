# -*- coding: utf-8 -*-

import csv
import os.path
from decimal import *

from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector

from jersey_electricity_items import JerseyElectricityMeta

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider
from product_spiders.base_spiders.amazonspider2.scraper import AmazonScraperProductDetailsException

HERE = os.path.abspath(os.path.dirname(__file__))

def format_price(price, rounding=None):
    if price is None:
        return Decimal('0.00')

    return price.quantize(Decimal('0.01'), rounding=rounding or ROUND_UP)


class JerseyElectricityAmazonBuyBox(BaseAmazonSpider):
    name = "jerseyelectricity-amazon-buybox"
    domain = "amazon.co.uk"

    type = 'search'
    only_buybox = True
    try_suggested = False

    max_pages = 1
    model_as_sku = True

    # the spider uses file, downloaded by main client's spider "jec.co.uk-feed" (jersey_feed.py)
    root = HERE
    file_path = os.path.join(root, 'Product_list.csv')

    def get_search_query_generator(self):
        with open(self.file_path) as f:
            reader = csv.DictReader(f, delimiter=',')
            for i, row in enumerate(reader, 1):
                sku = row['Product Reference']
                brand = row['Brand'].strip()
                search_term = brand + ' ' + sku
                product = {}
                yield search_term, product

        self.try_suggested = True

        with open(self.file_path) as f:
            reader = csv.DictReader(f, delimiter=',')
            for i, row in enumerate(reader, 1):
                name = row['Product Name']
                search_term = name
                product = {}
                yield search_term, product

    def match(self, meta, search_item, found_item):
        return True

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

        hxs = HtmlXPathSelector(response)

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

        if not product_info.get('sku'):
            product_info['sku'] = product_info['identifier'].replace(':', '')

        categories = hxs.select('//a[@class="nav-a nav-b"]/text()').extract()
        product_info['category'] = categories

        out_of_stock = 'OUT OF STOCK' in ''.join(hxs.select('//div[@id="availability"]/span/text()').extract()).strip().upper()
        if out_of_stock:
            product_info['stock'] = 0


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


    def construct_product(self, item, meta=None, use_seller_id_in_identifier=None):
        r = super(JerseyElectricityAmazonBuyBox, self).construct_product(item, meta, use_seller_id_in_identifier)
        metadata = JerseyElectricityMeta()
        metadata['site_price'] = r['price']
        r['metadata'] = metadata
        r['price'] = Decimal(r['price']) / Decimal('1.20') * Decimal('1.05')
        r['price'] = format_price(r['price'])
        return r

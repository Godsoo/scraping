# -*- coding: utf-8 -*-
"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4437
Type: buybox - extract price, which is displayed for "Buy" button

Description:

The way we are monitoring products on this site is going to be a little bit complicated.
This is the client feed www.wexphotographic.com/webcontent/productfeed/googlebase/gbproducts.txt

- Search GTIN
- If no results > Search MPN & brand
- If no results > Search product name

Only records with condition "new" should be used in search.

When there are results the spider should scrape whole page.

The spider should scrape options.
"""

import csv

import requests
from scrapy.utils.url import add_or_replace_parameter

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider, AmazonUrlCreator, AmazonScraper


class AmazonUrlCreatorException(Exception):
    pass


class AmazonUrlCreatorWex(AmazonUrlCreator):

    def __init__(self, *args, **kwargs):
        super(AmazonUrlCreatorWex, self).__init__(*args, **kwargs)

    @staticmethod
    def build_url_amazon_direct(domain, url):
        domain = AmazonUrlCreator._fix_domain(domain)

        if '.com' in domain:
            amazon_id = 'ATVPDKIKX0DER'
        elif '.co.uk' in domain:
            amazon_id = 'A3P5ROKL5A1OLE'
        elif '.fr' in domain:
            amazon_id = 'A1X6FK5RDHNB96'
        elif '.it' in domain:
            amazon_id = 'A11IL2PNWYJU7H'
        elif '.de' in domain:
            amazon_id = 'A3JWKAKR8XB7XF'
        elif '.ca' in domain:
            amazon_id = 'A3DWYIK6Y9EEQB'
        elif '.es' in domain:
            amazon_id = 'A1AT7YVPFBWXBL'
        else:
            raise AmazonUrlCreatorException('Domain %s not found!' % domain)

        url = add_or_replace_parameter(url, 'm', amazon_id)
        return url


class AmazonScraperWex(AmazonScraper):

    def __init__(self, *args, **kwargs):
        super(AmazonScraperWex, self).__init__(*args, **kwargs)

    def scrape_product_details_page(self, response, only_color=False, collect_new_products=True,
                                    collect_used_products=False):

        product = super(AmazonScraperWex, self).scrape_product_details_page(response, only_color, collect_new_products, collect_used_products)
        if product['options']:
            for option in product['options']:
                url = AmazonUrlCreatorWex.build_url_amazon_direct(AmazonUrlCreatorWex.get_domain_from_url(response.url), option['url'])
                option['url'] = url
        return product

    def scrape_search_results_page(self, response, amazon_direct=False):
        data = super(AmazonScraperWex, self).scrape_search_results_page(response, amazon_direct)
        for product in data['products']:
            url = AmazonUrlCreatorWex.build_url_amazon_direct(AmazonUrlCreatorWex.get_domain_from_url(response.url), product['url'])
            product['url'] = url
        return data


class WexPhotoNewAmazonBuybox(BaseAmazonSpider):
    domain = 'amazon.co.uk'
    name = 'wexphotographic_new-amazon_buybox'
    type = 'search'
    amazon_direct = True
    parse_options = True
    max_pages = 1
    try_suggested = False
    allowed_dealers = ['amazon']

    scraper_class = AmazonScraperWex

    collect_products_with_no_dealer = True

    def __init__(self, *args, **kwargs):
        super(WexPhotoNewAmazonBuybox, self).__init__(*args, **kwargs)
        self.to_process = {}

    def get_search_query_generator(self):
        r = requests.get('http://www.wexphotographic.com/webcontent/productfeed/googlebase/gbproducts.txt')
        reader = csv.DictReader(r.content.splitlines(), delimiter='|')
        for i, row in enumerate(reader):
            if row['condition'] != 'new':
                continue

            ean = row['gtin']
            sku = row['id']
            mpn = row['mpn']
            brand = row['brand']
            name = row['title']

            if sku in self.to_process:
                continue

            self.to_process[sku] = {
                'sku': sku,
                'ean': ean,
                'mpn': mpn,
                'brand': brand,
                'name': name,

                'ean_processed': False,
                'mpn_processed': False,

                'found': False
            }

        self.log("[WEX_NEW_AMAZON] Items to process: {}".format(len(self.to_process)))

        # EAN first
        for sku, row in self.to_process.items():
            if row['found']:
                continue
            search_item = {'sku': sku}

            if row['ean'] and not row['ean_processed']:
                self.to_process[sku]['ean_processed'] = True
                self.log("[WEX_NEW_AMAZON] Searching by EAN: {} (id: {})".format(row['ean'], sku))
                yield (row['ean'], search_item)

        processed_ean = {k: x for k, x in self.to_process.items() if x['found']}

        self.log("[WEX_NEW_AMAZON] Found using EAN: {}".format(len(processed_ean)))

        # then MPN
        for sku, row in self.to_process.items():
            if row['found']:
                continue
            search_item = {'sku': sku}

            if not row['mpn_processed']:
                self.to_process[sku]['mpn_processed'] = True
                search_str = "{} {}".format(row['brand'], row['mpn'])
                self.log("[WEX_NEW_AMAZON] Searching by MPN: {} (id: {})".format(search_str, sku))
                yield (search_str, search_item)

        processed_mpn = {k: x for k, x in self.to_process.items() if x['found'] and k not in processed_ean}

        self.log("[WEX_NEW_AMAZON] Found using MPN: {}".format(len(processed_mpn)))

        # then product name
        for sku, row in self.to_process.items():
            if row['found']:
                continue
            search_item = {'sku': sku}

            self.log("[WEX_NEW_AMAZON] Searching by product name: {} (id: {})".format(row['name'], sku))
            yield (row['name'], search_item)

        processed_name = {k: x for k, x in self.to_process.items()
                          if x['found'] and k not in processed_ean and k not in processed_mpn}

        self.log("[WEX_NEW_AMAZON] Found using product name: {}".format(len(processed_name)))

    def match(self, meta, search_item, found_item):
        # if got here then there is a match
        if 'sku' in search_item:
            sku = search_item['sku']
            self.to_process[sku]['found'] = True
        return True


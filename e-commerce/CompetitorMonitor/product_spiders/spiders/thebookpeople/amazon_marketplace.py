# -*- coding: utf-8 -*-
import csv
import os.path

from scrapy.http import Request

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider

from scrapy.selector import HtmlXPathSelector


HERE = os.path.abspath(os.path.dirname(__file__))


class AmazonSpider(BaseAmazonSpider):
    name = 'thebookpeople-amazon.co.uk-marketplace'
    domain = 'amazon.co.uk'

    type = 'search'

    all_sellers = True
    collect_new_products = True
    collect_used_products = False
    _use_amazon_identifier = True
    collected_identifiers = set()
    collect_products_from_list = False
    exclude_sellers = ['Amazon']

    collect_reviews = False

    try_suggested = False
    do_retry = True
    rotate_agent = True

    def get_search_query_generator(self):
        with open(os.path.join(HERE, 'thebookpeople.co.uk_products.csv')) as f:
            reader = csv.DictReader(f, delimiter=',')
            for row in reader:
                product = {'sku': ''}
                yield row['sku'], product

    def match(self, meta, search_item, found_item):
        return True

    def _process_product_info_product_details(self, response, product_info):
        """
        This needs to be in separate function because used by two methods: parse_product_details and parse_ajax_price
        """
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[@class="bucket"]/div[@class="content"]/ul/li[1]/a/text()').extract()
        product_info['category'] = categories

        sku = hxs.select('//li[b[contains(text(), "ISBN-13")]]/text()').extract()
        product_info['sku'] = sku[0].strip() if sku else ''

        if response.meta.get('seller_identifier', None) and not product_info.get('seller_identifier', None):
            product_info['seller_identifier'] = response.meta['seller_identifier']

        check_match = response.meta.get('check_match', True)

        match = self.match(response.meta, self.current_search_item, product_info)

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
                        meta=new_meta,
                        dont_filter=True
                    )
                return
            else:
                if product_info['name_with_options']:
                    product_info['name'] = product_info['name_with_options']
                elif product_info['option_texts']:
                    product_info['name'] += ' [' + ', '.join(product_info['option_texts']) + ']'

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
            if (product_info['price'] and product_info['vendor'] and self._seller_ok(product_info['vendor'])) or \
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
            elif not product_info['vendor'] or not product_info['price']:
                new_meta = response.meta.copy()
                new_meta['found_item'] = product_info
                new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': self.current_search_item,})
                yield Request(
                    product_info['mbc_list_url_new'],
                    callback=self.parse_mbc_list,
                    meta=new_meta
                )
                #self.log("[AMAZON] WARNING: product with no vendor: %s" % response.url)
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
                    self.log("[AMAZON] WARNING: Could not scrape vendor from product details: %s" % response.url)
                    self.errors.append("Could not scrape vendor from product details: %s" % response.url)
                else:
                    self.log("[AMAZON] WARNING: vendor not allowed: %s" % response.url)

import os
import re
import csv
from urlparse import urljoin
from scrapy.utils.response import get_base_url

from scrapy.http import Request

from scrapy.selector import HtmlXPathSelector
from product_spiders.utils import extract_price


HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider, AmazonUrlCreator


class TheBookPeopleAmazonBuyboxSpider(BaseAmazonSpider):
    name = 'thebookpeople-amazon.co.uk-buybox'
    domain = 'www.amazon.co.uk'
    max_pages = 1
    do_retry = True
    retry_sleep = 10
    collect_new_products = True
    collect_used_products = False
    only_buybox = True
    dealer_is_mandatory = True
    collect_products_with_no_dealer = True
    try_suggested = False
    collect_products_with_no_dealer = False

    second_code_list = {}

    def __init__(self, *args, **kwargs):
        super(TheBookPeopleAmazonBuyboxSpider, self).__init__(*args, **kwargs)
        self.try_suggested = False
        self.current_searches = []

    def start_requests(self):
        requests = []
        with open(os.path.join(HERE, 'thebookpeople_products.csv')) as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if row['amazon']:
                    search_item = {'sku': row['ISBN'],
                           'name': '',
                           'category':'',
                           'price': '',
                          }
                    requests.append(Request(row['amazon'], meta={'search_string': '', 'search_item': search_item},
                        dont_filter=True, callback=self.parse_product))
        return requests

    def match(self, meta, search_item, found_item):
        return True

    def _collect_buybox(self, product, meta):
        self._collect_all(product)

    def _process_product_info_product_details(self, response, product_info):
        """
        This needs to be in separate function because used by two methods: parse_product_details and parse_ajax_price
        """
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[@class="bucket"]/div[@class="content"]/ul/li[1]/a/text()').extract()
        product_info['category'] = categories

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

    def _process_product_list_item_buybox(self, response, item):
        """
        Must yield value of matched_any as last element
        """
        matched_any = False
        match = self.match(response.meta, self.current_search_item, item)
        if match:
            matched_any = True
            if self.parse_options or self.dealer_is_mandatory or self.model_as_sku:
                new_meta = response.meta.copy()
                new_meta['check_match'] = False
                new_meta['found_item'] = item
                if self.type == 'search':
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': self.current_search_item,
                    })
                yield Request(
                    item['url'],
                    callback=self.parse_product,
                    meta=new_meta
                )
            elif self.collect_reviews and item['reviews_url']:
                # yield reviews parse
                new_meta = response.meta.copy()
                new_meta['found_item'] = item
                if self.type == 'search':
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': self.current_search_item,
                    })
                yield Request(
                    item['reviews_url'],
                    callback=self.parse_reviews,
                    meta=new_meta
                )

            else:
                product = self.construct_product(item, meta=response.meta)
                product['dealer'] = ''

                # collect product
                if self.type == 'category':
                    self.log("[AMAZON] Scraping product %s (%s) from url %s" %
                             (product['name'], product['identifier'], response.url))
                    yield product
                else:
                    self.log("[AMAZON] Collecting product %s (%s) from url %s" %
                             (product['name'], product['identifier'], response.url))
                    self._collect_buybox(product, response.meta)
        elif self.try_match_product_details_if_product_list_not_matches:
            # go to product details page to extract SKU and try matching again
            new_meta = response.meta.copy()
            new_meta['check_match'] = True
            if self.type == 'search':
                new_meta.update({
                    'search_string': response.meta['search_string'],
                    'search_item': self.current_search_item,
                })
            yield Request(
                item['url'],
                callback=self.parse_product,
                meta=new_meta
            )

        yield matched_any

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

        hxs = HtmlXPathSelector(response)
        unavailable = 'CURRENTLY UNAVAILABLE' in ''.join(hxs.select('//div[@id="buybox"]/div[@id="outOfStock"]//div//text()').extract()).upper()
        if unavailable:
            return

        # Fix self.current_search_item and meta['search_item']. Needed for BSM spider
        #if not response.meta.get('search_item'):
        #    response.meta['search_item'] = product_info
        #if not self.current_search_item:
        self.current_search_item = response.meta['search_item']

        #product_info['price'] = response.meta['found_item']['price']

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

        if not product_info['mbc_list_url_new']:
            base_url = get_base_url(response)
            mbc_url = hxs.select('//span[@class="olp-new olp-link"]/a/@href').extract()
            if mbc_url:
                product_info['mbc_list_url_new'] = urljoin(base_url, mbc_url[0])
            else:
                mbc_url = hxs.select('//td[contains(@class, "dp-new-col")]/a/@href').extract()
                if mbc_url:
                    product_info['mbc_list_url_new'] = urljoin(base_url, mbc_url[0])
        for res in self._process_product_info_product_details(response, product_info):
            yield res

    def parse_mbc_list(self, response):
        if self.scraper.antibot_protection_raised(response.body_as_unicode()):
            self.antibot_blocked_count += 1
            if self.should_do_retry(response):
                self.log('[AMAZON] WARNING: Amazon antibot protection detected when crawling url: %s' %
                         response.url)
                yield self.retry_download(url=response.url,
                                          metadata=response.meta,
                                          callback=self.parse_mbc_list)
                return
            else:
                self.antibot_blocked_fully_urls.add(response.url)
                self.log('[AMAZON] WARNING: '
                         'Amazon antibot protection detected, consider using proxy/tor, url: [{}]'.format(response.url))
                return

        self.parsed_count['parse_mbc_list'] += 1

        results = self.scraper.scrape_mbc_list_page(response)

        if not results:
            if self.should_do_retry(response):
                self.log("[[AMAZON]] Reloading MBC list: %s" % response.url)
                yield self.retry_download(url=response.url,
                                          metadata=response.meta,
                                          callback=self.parse_mbc_list)
            return

        for item in results['products'][0:1]:
            if response.meta.get('found_item'):
                base_item = response.meta['found_item'].copy()
                base_item.update(item)
                item = base_item
            if item['price'] is None:
                new_meta = response.meta.copy()
                new_meta.update({
                    '_product': item,
                    'check_match': False,
                    'collect_mbc': False,
                    'parse_options': False
                })
                if self.type == 'search':
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': self.current_search_item,
                    })
                yield Request(
                    item['url'],
                    callback=self.parse_product,
                    dont_filter=True,
                    meta=new_meta
                )
            elif item['vendor']:
                self._add_seller_to_cache(item['seller_identifier'], item['vendor'])
                if self._seller_ok(item['vendor']):
                    self.log('[AMAZON] COLLECTED ITEM => %s' % item['name'])
                    use_seller_id_in_identifier = False \
                            if self.lowest_product_and_seller and not self.lowest_seller_collect_dealer_identifier else True
                    product = self.construct_product(item, meta=response.meta,
                                                     use_seller_id_in_identifier=use_seller_id_in_identifier)
                    if self.type == 'category' and not self.collect_reviews:
                        yield product
                    else:
                        self._collect(product)
            elif self._get_seller_from_cache(item['seller_identifier']):
                seller_name = self._get_seller_from_cache(item['seller_identifier'])
                item['vendor'] = seller_name
                if self._seller_ok(item['vendor']):
                    self.log('[AMAZON] COLLECTED ITEM => %s' % item['name'])
                    use_seller_id_in_identifier = False \
                            if self.lowest_product_and_seller and not self.lowest_seller_collect_dealer_identifier else True
                    product = self.construct_product(item, meta=response.meta,
                                                     use_seller_id_in_identifier=use_seller_id_in_identifier)
                    if self.type == 'category' and not self.collect_reviews:
                        yield product
                    else:
                        self._collect(product)
            elif item['seller_identifier']:
                new_meta = response.meta.copy()
                new_meta.update({
                    '_product': item,
                    'seller_identifier': item['seller_identifier'],
                    'check_match': False,
                    'collect_mbc': False,
                    'parse_options': False
                })
                if self.type == 'search':
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': self.current_search_item,
                    })
                yield Request(
                    item['seller_url'],
                    callback=self.parse_vendor,
                    dont_filter=True,
                    meta=new_meta
                )
            else:
                self.log("[AMAZON] WARNING: no seller identifier on %s" % response.url)

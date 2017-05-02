# -*- coding: utf-8 -*-
__author__ = 'juraseg'

from scrapy.http import Request

from product_spiders.utils import url_quote
from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider
from product_spiders.spiders.sagemcom.utils import get_product_list


class AmazonCoUkSagemcomSpider(BaseAmazonSpider):
    name = 'amazon.co.uk_sagemcom'
    domain = 'amazon.co.uk'

    type = 'search'

    only_buybox = True

    parse_options = False
    collect_products_with_no_dealer = True

    semicolon_in_identifier = False

    search_url = 'http://www.amazon.co.uk/s/ref=nb_sb_noss?url=search-alias%3Delectronics&field-keywords='

    def __init__(self, *args, **kwargs):
        super(AmazonCoUkSagemcomSpider, self).__init__(*args, **kwargs)
        self.product_found = None

    def get_search_query_generator(self):
        for row in get_product_list('Amazon'):
            if row['url']:
                yield row['url'], self.parse_product, row['search'][0], row
            else:
                original_query = row['search'].pop(0)
                query = url_quote(original_query)
                url = self.search_url + query
                yield url, self.parse_product_list, original_query, row

    def process_next_step(self, spider):
        if self.collected_items:
            self.product_found = True
        return super(AmazonCoUkSagemcomSpider, self).process_next_step(spider)

    def get_next_search_request(self, callback=None):
        """
        Creates search request using self.search_generator
        """
        if self.product_found is not None and not self.product_found and self.current_search_item['search']:
            self.log("[[TESTING]] Resuming current search: %s" % str(self.current_search_item))
            search_string = self.current_search_item['search'].pop(0)
            url = self.search_url + search_string.replace(' ', '+')
            callback = self.parse_product_list
            search_item = self.current_search_item
        else:
            self.log("[[TESTING]] Starting new search")
            if not self.search_generator:
                return []
            try:
                url, callback, search_string, search_item = next(self.search_generator)
            except StopIteration:
                return []
            self.product_found = False

        self.log('[AMAZON] Searching for [%s]' % search_string)

        self.current_search = search_string
        self.current_search_item = search_item
        self.collected_items = []
        self.processed_items = False

        request = Request(url, callback, dont_filter=True, meta={
            'search_string': search_string,
            'search_item': search_item
        })

        return [request]

    def match(self, meta, search_item, found_item):
        return True

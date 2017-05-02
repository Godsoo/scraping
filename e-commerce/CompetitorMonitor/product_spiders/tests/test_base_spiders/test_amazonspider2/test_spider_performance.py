# -*- coding: utf-8 -*-
import os.path
import timeit
from itertools import product

from scrapy.http.request import Request

from product_spiders.response_utils import retrieve_response
from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider
from product_spiders.tests.test_base_spiders.test_amazonspider2.base_spider_test_case import AmazonBaseTestCase
from product_spiders.tests.test_base_spiders.test_amazonspider2.test_scraper import fixtures_path


class TestAmazonSpiderParseProductsList(AmazonBaseTestCase):
    def _build_spider(self, spider_type='amazon_direct', reviews_enabled=False):
        class TestSpider(BaseAmazonSpider):
            name = 'Test Spider'
            type = 'search'
            domain = 'amazon.com'

            def match(self, meta, search_item, found_item):
                return True

        spider = TestSpider()
        spider.collected_items = []
        spider.current_search_item = None
        spider.current_search = ''
        if spider_type == 'amazon_direct':
            spider.amazon_direct = True
        elif spider_type == 'only_buybox':
            spider.only_buybox = True
        elif spider_type == 'all_sellers':
            spider.all_sellers = True
        else:
            raise ValueError("Unknow spider type: {}".format(spider_type))
        if reviews_enabled:
            spider.collect_reviews = True
            spider.reviews_only_matched = False
        return spider

    def test_parse_products_list(self):
        """
        Checks that "parse_product_list" method does not take more than 1 ms to execute.

        There are different configurations of spiders affecting method run, we test them all.
        """
        types = ['amazon_direct', 'only_buybox', 'all_sellers']
        review_types = [True, False]
        for spider_type, reviews_enabled in product(types, review_types):
            spider = self._build_spider(spider_type, reviews_enabled)
            response = retrieve_response(os.path.join(fixtures_path, 'search1'))
            request = Request(
                'http://www.amazon.co.uk/s/ref=nb_sb_noss?url=search-alias%3Daps&field-keywords=LEGO%2010188',
                callback=spider.parse_product_list)
            response.request = request

            def __under_test():
                spider.parse_product_list(response)

            repeats = 100000
            time = timeit.timeit(__under_test, number=repeats)
            self.assertLess(time / repeats, 0.0001, "Too slow in spider {} with reviews {}".format(
                spider_type, 'enabled' if reviews_enabled else 'disabled'))

    def test_parse_mbc_list(self):
        """
        Checks that "parse_mbc_list" method does not take more than 1 ms to execute.

        There are different configurations of spiders affecting method run, we test them all.
        """
        types = ['amazon_direct', 'only_buybox', 'all_sellers']
        review_types = [True, False]
        for spider_type, reviews_enabled in product(types, review_types):
            spider = self._build_spider(spider_type, reviews_enabled)
            response = retrieve_response(os.path.join(fixtures_path, 'mbc_list'))
            request = Request(
                'http://www.amazon.co.uk/gp/offer-listing/B002EEP3NO/ref=sr_1_1_olp/'
                '279-2607573-2864855?ie=UTF8&qid=1395239715&sr=8-1&keywords=LEGO+10188&condition=new',
                callback=spider.parse_product_list)
            response.request = request

            def __under_test():
                spider.parse_mbc_list(response)

            repeats = 100000
            time = timeit.timeit(__under_test, number=repeats)
            self.assertLess(time / repeats, 0.0001, "Too slow in spider {} with reviews {}".format(
                spider_type, 'enabled' if reviews_enabled else 'disabled'))

# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import random
import unittest

from scrapy.exceptions import CloseSpider, DontCloseSpider
from scrapy.http import Request

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider, AmazonUrlCreator
from product_spiders.tests.test_base_spiders.test_amazonspider2.base_spider_test_case import MockEngine, MockCrawler


class TestAmazonSpiderSeveralTypes(unittest.TestCase):
    def test_start_request_returns_list_with_one_request(self):
        engine = MockEngine()
        crawler = MockCrawler(engine)

        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = ['asins', 'search']

            def get_asins_generator(self):
                for text in ["BA123", "BA456"]:
                    item = {'asin': text, 'sku': '', 'identifier': text}
                    yield item['asin'], item['sku']

            def get_search_query_generator(self):
                for text in ["Lego 123", "Lego 456"]:
                    item = {'identifier': text, 'name': text, 'sku': text, 'price': random.randint(100, 1000) / 10.0}
                    yield item['name'], item

        spider = TestSpider('amazon.com')
        spider.crawler = crawler
        spider.start_requests()
        self.assertEqual(spider.type, 'asins')
        # process next ASIN
        self.assertRaises(DontCloseSpider, spider.process_next_step, spider=spider)
        # change type to search and process first search query
        self.assertRaises(DontCloseSpider, spider.process_next_step, spider=spider)
        self.assertEqual(spider.type, 'search')

        # next search query
        self.assertRaises(DontCloseSpider, spider.process_next_step, spider=spider)
        # change type to None
        spider.process_next_step(spider)

        self.assertIsNone(spider.type)
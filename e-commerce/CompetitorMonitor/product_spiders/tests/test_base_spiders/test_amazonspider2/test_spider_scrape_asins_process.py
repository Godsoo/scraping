# coding=utf-8
__author__ = 'juraseg'

import random
import unittest

from scrapy.exceptions import CloseSpider, DontCloseSpider
from scrapy.http import Request

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider, AmazonUrlCreator
from product_spiders.tests.test_base_spiders.test_amazonspider2.base_spider_test_case import MockEngine, MockCrawler


class TestAmazonSpiderScrapeAsinsProcess(unittest.TestCase):
    def test_raised_close_spider_when_no_asins(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = 'asins'
            def get_asins_generator(self):
                return

        spider = TestSpider('amazon.com')

        self.assertEqual(spider.start_requests(), [])

    def test_raises_not_implemented_error_when_no_asin_generator_func(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = 'asins'

        spider = TestSpider('amazon.com')

        with self.assertRaises(NotImplementedError) as cm:
            spider.start_requests()

        self.assertEqual(str(cm.exception), "Spider should implement method `get_asins_generator`!")

    def test_start_request_returns_list_with_one_request(self):
        mock_items = []
        for text in ["BA123", "BA456"]:
            mock_items.append({'asin': text, 'sku': '', 'identifier': text})

        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = 'asins'
            def get_asins_generator(self):
                for item in mock_items[:]:
                    yield item['asin'], item['sku']

        spider = TestSpider('amazon.com')

        requests = spider.start_requests()

        self.assertEqual(len(requests), 1)
        self.assertIsInstance(requests[0], Request)
        self.assertEqual(spider.current_search, '')
        self.assertEqual(spider.current_search_item, mock_items[0])

    def test_get_asin_request_returns_request_with_correct_data(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = 'asins'
            def get_asins_generator(self):
                for text in ["BA123", "BA456"]:
                    item = {'asin': text, 'sku': text.lower()}
                    yield item['asin'], item['sku']

        spider = TestSpider('amazon.com')

        spider.asins_generator = spider.get_asins_generator()

        def callback(response):
            pass

        requests = spider.get_next_asin_request(callback)

        self.assertEqual(len(requests), 1)

        request = requests[0]

        self.assertIsInstance(request, Request)
        self.assertEqual(request.method, 'GET')
        self.assertIs(request.callback, callback)
        self.assertTrue(request.dont_filter)
        self.assertEqual(request.meta['search_item']['asin'], "BA123")
        self.assertEqual(request.meta['search_item']['sku'], "BA123".lower())

class TestAmazonSpiderNextStepAsinsType(unittest.TestCase):
    """
    Tests `process_next_step` method and related methods
    """
    def test_process_next_step_redirects_to_next_search(self):
        engine = MockEngine()
        crawler = MockCrawler(engine)

        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = 'asins'
            def get_asins_generator(self):
                for text in ["BA123", "BA456"]:
                    item = {'asin': text, 'sku': text.lower()}
                    yield item['asin'], item['sku']

        spider = TestSpider('amazon.com')
        spider.crawler = crawler

        spider.start_requests()
        spider.collected_items = []

        self.assertRaises(DontCloseSpider, spider.process_next_step, spider)
        request = engine.last_request

        self.assertEqual(engine.crawl_called, 1)

        # check redirects to home page
        self.assertIs(spider, engine.last_spider)
        self.assertEqual(request.url, AmazonUrlCreator.build_url_from_asin('amazon.com', "BA456"))
        self.assertTrue(request.dont_filter)
        self.assertEqual(request.meta['search_item']['asin'], "BA456")
        self.assertEqual(request.meta['search_item']['sku'], "BA456".lower())

        # check callback yields items
        self.assertEqual(request.callback, spider.parse_product)

    def test_process_next_step_returns_none_when_nothing_to_process(self):
        engine = MockEngine()
        crawler = MockCrawler(engine)

        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = 'asins'
            def get_asins_generator(self):
                for text in ["BA123"]:
                    item = {'asin': text, 'sku': text.lower()}
                    yield item['asin'], item['sku']

        spider = TestSpider('amazon.com')
        spider._crawler = crawler

        # processing the only search request we have
        spider.start_requests()
        spider.collected_items = []

        spider.process_next_step(spider)

        self.assertEqual(engine.crawl_called, 0)

        # check redirects to home page
        self.assertIsNone(engine.last_spider)
        self.assertIsNone(engine.last_request)
# coding=utf-8
__author__ = 'juraseg'

import unittest
import mock

from scrapy.exceptions import CloseSpider, DontCloseSpider
from scrapy.http import Request

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider, AmazonProduct
from product_spiders.tests.test_base_spiders.test_amazonspider2.base_spider_test_case import \
    MockEngine, MockCrawler, AmazonBaseTestCase


class TestAmazonSpiderScrapeCategoryProcess(unittest.TestCase):
    def test_raised_close_spider_when_no_category_urls(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = 'category'
            def get_category_url_generator(self):
                return

        spider = TestSpider('amazon.com')

        self.assertEqual(spider.start_requests(), [])

    def test_raises_not_implemented_error_when_no_category_url_generator_func(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = 'category'

        spider = TestSpider('amazon.com')

        with self.assertRaises(NotImplementedError) as cm:
            spider.start_requests()

        self.assertEqual(str(cm.exception), "Spider should implement method `get_category_url_generator`!")

    def test_start_request_returns_list_with_one_request(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = 'category'
            def get_category_url_generator(self):
                for url in [('http://url1', 'cat1'), ('http://url2', 'cat2')]:
                    yield url

        spider = TestSpider('amazon.com')

        requests = spider.start_requests()

        self.assertEqual(len(requests), 1)
        self.assertIsInstance(requests[0], Request)

    def test_get_category_url_request_returns_request_with_correct_data(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = 'category'
            def get_category_url_generator(self):
                for url in [('http://url1', 'cat1'), ('http://url2', 'cat2')]:
                    yield url

        spider = TestSpider('amazon.com')

        spider.category_url_generator = spider.get_category_url_generator()

        def callback(response):
            pass

        requests = spider.get_next_category_request(callback)

        self.assertEqual(len(requests), 1)

        request = requests[0]

        self.assertIsInstance(request, Request)
        self.assertEqual(request.method, 'GET')
        self.assertEqual(request.url, 'http://url1')
        self.assertIs(request.callback, callback)
        self.assertTrue(request.dont_filter)
        self.assertNotIn('search_item', request.meta)
        self.assertNotIn('search_string', request.meta)
        self.assertEqual(spider.current_category, 'cat1')
        self.assertEqual(request.meta['category'], 'cat1')

class TestAmazonSpiderNextStepCategoryType(unittest.TestCase):
    """
    Tests `process_next_step` method and related methods
    """
    def test_process_next_step_redirects_to_next_search(self):
        engine = MockEngine()
        crawler = MockCrawler(engine)

        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = 'category'
            def get_category_url_generator(self):
                for url in [('http://url1', 'cat1'), ('http://url2', 'cat2')]:
                    yield url

        spider = TestSpider('amazon.com')
        spider.crawler = crawler

        spider.start_requests()
        spider.collected_items = []

        self.assertRaises(DontCloseSpider, spider.process_next_step, spider)
        request = engine.last_request

        self.assertEqual(engine.crawl_called, 1)

        # check redirects to home page
        self.assertIs(spider, engine.last_spider)
        self.assertTrue(request.dont_filter)
        self.assertEqual(request.url, 'http://url2')
        self.assertNotIn('search_item', request.meta)
        self.assertNotIn('search_string', request.meta)
        self.assertEqual(spider.current_category, 'cat2')
        self.assertEqual(request.meta['category'], 'cat2')

        # check callback yields items
        self.assertEqual(request.callback, spider.parse_product_list)

    def test_process_next_step_returns_none_when_nothing_to_process(self):
        engine = MockEngine()
        crawler = MockCrawler(engine)

        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = 'category'
            def get_category_url_generator(self):
                for url in [('http://url1', 'cat1')]:
                    yield url

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

class TestAmazonSpiderCategoryParsing(AmazonBaseTestCase):
    def _get_spider(self, mock_scraper):

        class TestSpider(BaseAmazonSpider):
            name = 'Test Spider'
            type = 'category'
            domain = 'amazon.com'

        spider = TestSpider()
        spider.scraper = mock_scraper
        spider.collected_items = []
        spider.current_search_item = None
        spider.current_search = ''

        return spider

    # buybox mode
    def test_buybox_parse_product_list_redirects_to_product_details_to_get_dealer(self):
        spider = self._get_spider(self._get_mock_scraper_products_list())
        spider.only_buybox = True
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {})

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), len(self._get_mock_items()))

        expected_urls = [x['url'] for x in self._get_mock_items()]

        for request in results:
            self.assertEqual(request.callback, spider.parse_product)
            self.assertIn(request.url, expected_urls)
            self.assertFalse(request.meta.get('check_match', False))

    def test_buybox_parse_product_details_yields_product(self):
        spider = self._get_spider(self._get_mock_scraper_product_details())
        spider.only_buybox = True
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            {}
        )

        results = list(spider.parse_product(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), 1)

        item = results[0]
        self.assertIsInstance(item, AmazonProduct)

    def test_buybox_parse_product_details_redirects_to_reviews_when_needed(self):
        spider = self._get_spider(self._get_mock_scraper_product_details())
        spider.only_buybox = True
        spider.collect_reviews = True
        spider.reviews_only_matched = False
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            {}
        )

        results = list(spider.parse_product(mock_response))

        # product is collected
        self.assertEqual(len(spider.collected_items), 1)
        self.assertEqual(len(results), 1)

        expected_url = self._get_mock_item()['reviews_url']

        request = results[0]
        self.assertEqual(request.callback, spider.parse_reviews)
        self.assertEqual(request.url, expected_url)

    # amazon direct mode
    def test_amazon_direct_parse_product_list_yields_products(self):
        spider = self._get_spider(self._get_mock_scraper_products_list())
        spider.amazon_direct = True
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {})

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), len(self._get_mock_items()))

        for item in results:
            self.assertIsInstance(item, AmazonProduct)

    def test_amazon_direct_parse_product_list_redirects_to_product_details_when_options_needed(self):
        spider = self._get_spider(self._get_mock_scraper_products_list())
        spider.amazon_direct = True
        spider.parse_options = True
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {})

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), len(self._get_mock_items()))

        expected_urls = [x['url'] for x in self._get_mock_items()]

        for request in results:
            self.assertEqual(request.callback, spider.parse_product)
            self.assertIn(request.url, expected_urls)
            self.assertFalse(request.meta.get('check_match', False))

    def test_amazon_direct_parse_product_list_redirects_to_reviews_when_reviews_needed(self):
        spider = self._get_spider(self._get_mock_scraper_products_list())
        spider.amazon_direct = True
        spider.collect_reviews = True
        spider.reviews_only_matched = False
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {})

        results_gen = spider.parse_product_list(mock_response)
        results = []
        for request in results_gen:
            results.append(request)

        # products are collected
        self.assertEqual(len(spider.collected_items), 2)
        self.assertEqual(len(results), len(self._get_mock_items()))

        expected_urls = [x['reviews_url'] for x in self._get_mock_items()]

        for request in results:
            self.assertEqual(request.callback, spider.parse_reviews)
            self.assertIn(request.url, expected_urls)
            self.assertFalse(request.meta.get('check_match', False))

    def test_amazon_direct_parse_product_details_yields_product(self):
        spider = self._get_spider(self._get_mock_scraper_product_details())
        spider.amazon_direct = True
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            {}
        )

        results = list(spider.parse_product(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), 1)

        item = results[0]
        self.assertIsInstance(item, AmazonProduct)

    def test_amazon_direct_parse_product_details_redirects_to_reviews_when_needed(self):
        spider = self._get_spider(self._get_mock_scraper_product_details())
        spider.amazon_direct = True
        spider.collect_reviews = True
        spider.reviews_only_matched = False
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            {}
        )

        results = list(spider.parse_product(mock_response))
        # product is collected
        self.assertEqual(len(spider.collected_items), 1)
        self.assertEqual(len(results), 1)
        request = results[0]
        self.assertIsInstance(request, Request)
        expected_url = self._get_mock_item()['reviews_url']
        self.assertEqual(request.callback, spider.parse_reviews)
        self.assertEqual(request.url, expected_url)

        spider.reviews_only_matched = True
        spider.matched_product_asins = {self._get_mock_item()['asin']}
        results = list(spider.parse_product(mock_response))
        # product is collected
        self.assertEqual(len(spider.collected_items), 1)
        self.assertEqual(len(results), 1)
        request = results[0]
        self.assertIsInstance(request, Request)
        expected_url = self._get_mock_item()['reviews_url']
        self.assertEqual(request.callback, spider.parse_reviews)
        self.assertEqual(request.url, expected_url)

    # test all sellers mode
    def test_all_sellers_parse_product_list_redirects_to_product_details_when_options_needed(self):
        spider = self._get_spider(self._get_mock_scraper_products_list())
        spider.all_sellers = True
        spider.parse_options = True
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {})

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), len(self._get_mock_items()))

        expected_urls = [x['url'] for x in self._get_mock_items()]

        for request in results:
            self.assertEqual(request.callback, spider.parse_product)
            self.assertIn(request.url, expected_urls)
            self.assertFalse(request.meta.get('check_match', False))

    def test_all_sellers_parse_product_list_redirects_to_mbc_list(self):
        spider = self._get_spider(self._get_mock_scraper_products_list())
        spider.all_sellers = True
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {'search_string': 'item'})

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), len(self._get_mock_items()))

        expected_urls = [x['mbc_list_url_new'] for x in self._get_mock_items()]

        for request in results:
            self.assertEqual(request.callback, spider.parse_mbc_list)
            self.assertIn(request.url, expected_urls)

    def test_stops_if_non_specific_category_results(self):
        spider = self._get_spider(self._get_mock_scraper_products_list(is_non_specific_cat_results=True))
        spider.all_sellers = True
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {'search_string': 'item'})

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(results), 0)
        self.assertEqual(len(spider.collected_items), 0)

    # TODO: test uses model number as sku

# -*- coding: utf-8 -*-
import random
import unittest

from scrapy.exceptions import CloseSpider, DontCloseSpider
from scrapy.http import Request

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider, AmazonUrlCreator
from product_spiders.tests.test_base_spiders.test_amazonspider2.base_spider_test_case import MockEngine, MockCrawler


class TestAmazonSpiderSearchProcess(unittest.TestCase):
    """
    Tests search process in overall
    """
    def test_raised_close_spider_when_no_search(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            def get_search_query_generator(self):
                return

        spider = TestSpider('amazon.com')

        self.assertEqual(spider.start_requests(), [])

    def test_raises_not_implemented_error_when_no_search_generator_func(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"

        spider = TestSpider('amazon.com')

        with self.assertRaises(NotImplementedError) as cm:
            spider.start_requests()

        self.assertEqual(str(cm.exception), "Spider should implement method `get_search_query_generator`!")

    def test_start_request_returns_list_with_one_request(self):
        mock_items = []
        for text in ["Lego 123", "Lego 456"]:
            mock_items.append({'identifier': text, 'name': text, 'sku': text, 'price': random.randint(100, 1000) / 10.0})

        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            def get_search_query_generator(self):
                random.seed()
                for item in mock_items[:]:
                    yield item['name'], item

        spider = TestSpider('amazon.com')

        requests = spider.start_requests()

        self.assertEqual(len(requests), 1)
        self.assertIsInstance(requests[0], Request)
        self.assertEqual(spider.current_search, mock_items[0]['name'])
        self.assertEqual(spider.current_search_item, mock_items[0])

    def test_get_search_request_fails_if_without_start_requests(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
            def get_search_query_generator(self):
                random.seed()
                for text in ["Lego 123", "Lego 456"]:
                    item = {'identifier': text, 'name': text, 'sku': text, 'price': random.randint(100, 1000) / 10.0}
                    yield text, item

        spider = TestSpider()

        def callback(response):
            pass

        requests = spider.get_next_search_request(callback)

        self.assertEqual(len(requests), 0)

    def test_get_search_request_returns_request_with_correct_data(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            def get_search_query_generator(self):
                random.seed()
                for text in ["Lego 123", "Lego 456"]:
                    item = {'identifier': text, 'name': text, 'sku': text, 'price': random.randint(100, 1000) / 10.0}
                    yield text, item

        spider = TestSpider('amazon.com')

        spider.search_generator = spider.get_search_query_generator()

        def callback(response):
            pass

        requests = spider.get_next_search_request(callback)

        self.assertEqual(len(requests), 1)

        request = requests[0]

        self.assertIsInstance(request, Request)
        self.assertEqual(request.method, 'GET')
        self.assertIs(request.callback, callback)
        self.assertTrue(request.dont_filter)
        self.assertEqual(request.meta['search_string'], "Lego 123")
        self.assertEqual(request.meta['search_item']['identifier'], "Lego 123")


class TestAmazonSpiderNextStepSearchType(unittest.TestCase):
    def test_process_next_step_redirects_to_next_search(self):
        engine = MockEngine()
        crawler = MockCrawler(engine)

        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            def get_search_query_generator(self):
                random.seed()
                for text in ["Lego 123", "Lego 456"]:
                    item = {'identifier': text, 'name': text, 'sku': text, 'price': random.randint(100, 1000) / 10.0}
                    yield text, item

        spider = TestSpider('amazon.com')
        spider.crawler = crawler

        spider.start_requests()
        spider.collected_items = []

        self.assertRaises(DontCloseSpider, spider.process_next_step, spider)
        request = engine.last_request

        self.assertEqual(engine.crawl_called, 1)

        # check redirects to home page
        self.assertIs(spider, engine.last_spider)
        self.assertEqual(request.url, AmazonUrlCreator.build_search_url('amazon.com', "Lego 456"))
        self.assertTrue(request.dont_filter)
        self.assertEqual(request.meta['search_string'], "Lego 456")
        self.assertEqual(request.meta['search_item']['identifier'], "Lego 456")

        # check callback yields items
        self.assertEqual(request.callback, spider.parse_product_list)

    def test_process_next_step_returns_none_when_nothing_to_process(self):
        engine = MockEngine()
        crawler = MockCrawler(engine)

        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            def get_search_query_generator(self):
                random.seed()
                for text in ["Lego 123"]:
                    item = {'identifier': text, 'name': text, 'sku': text, 'price': random.randint(100, 1000) / 10.0}
                    yield text, item

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

class TestAmazonSpiderProcessNextStep(unittest.TestCase):
    """
    Tests `process_next_step` method and related methods
    """
    def test_process_next_step_redirects_to_process_products(self):
        engine = MockEngine()
        crawler = MockCrawler(engine)

        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            def get_search_query_generator(self):
                random.seed()
                for text in ["Lego 123", "Lego 456"]:
                    item = {'identifier': text, 'name': text, 'sku': text, 'price': random.randint(100, 1000) / 10.0}
                    yield text, item

        spider = TestSpider('amazon.com')
        spider.crawler = crawler

        spider.start_requests()
        mock_items = [
            {
                'name': 'item1',
                'identifier': 'id1',
            },
            {
                'name': 'item2',
                'identifier': 'id2',
            }
        ]
        spider.collected_items = mock_items[:]

        self.assertRaises(DontCloseSpider, spider.process_next_step, spider)
        request = engine.last_request

        self.assertEqual(engine.crawl_called, 1)

        # check redirects to home page
        self.assertIs(spider, engine.last_spider)
        self.assertEqual(request.url, 'file:///etc/hosts')
        self.assertTrue(request.dont_filter)

        # check callback yields items
        result_gen = request.callback("the response")
        for res in result_gen:
            self.assertIn(res, mock_items)

        # check collected items emptied after processing them
        self.assertEqual(len(spider.collected_items), 0)

    def test_process_collected_products_collects_products(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            def get_search_query_generator(self):
                random.seed()
                for text in ["Lego 123"]:
                    item = {'identifier': text, 'name': text, 'sku': text, 'price': random.randint(100, 1000) / 10.0}
                    yield text, item

        spider = TestSpider('amazon.com')
        mock_items = [
            {
                'name': 'item1',
                'identifier': 'id1',
            },
            {
                'name': 'item2',
                'identifier': 'id2',
            }
        ]
        spider.collected_items = mock_items[:]

        results = list(spider.process_collected_products())

        self.assertEqual(len(results), len(mock_items))
        for item in results:
            self.assertIn(item, mock_items)
        self.assertEqual(len(spider.collected_items), 0)
        self.assertTrue(spider.processed_items)

    def test_process_collected_products_add_reviews_to_products(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            collect_reviews = True
            domain = 'amazon.com'
            def get_search_query_generator(self):
                random.seed()
                for text in ["Lego 123"]:
                    item = {'identifier': text, 'name': text, 'sku': text, 'price': random.randint(100, 1000) / 10.0}
                    yield text, item

        spider = TestSpider()

        mock_items = [
            {
                'identifier': 'id1',
                'name': 'name1'
            },
            {
                'identifier': 'id2',
                'name': 'name2'
            },
            {
                'identifier': 'id3',
                'name': 'name3'
            }
        ]
        mock_reviews = {
            'id1': ['review1', 'review2'],
            'id2': ['review3']
        }
        spider.collected_items = mock_items[:]
        spider.collected_reviews = mock_reviews.copy()

        results = list(spider.process_collected_products())

        self.assertEqual(len(results), len(mock_items))
        for item in results:
            self.assertIn(item, mock_items)
            if item['identifier'] in mock_reviews:
                self.assertIn('metadata', item.keys())
                self.assertIn('reviews', item['metadata'])
                self.assertEqual(len(item['metadata']['reviews']), len(mock_reviews[item['identifier']]))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertTrue(spider.processed_items)

    def test_process_collected_products_add_reviews_to_products_with_seller_ids(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            collect_reviews = True
            all_sellers = True
            reviews_once_per_product_without_dealer = False

            def get_search_query_generator(self):
                random.seed()
                for text in ["Lego 123"]:
                    item = {'identifier': text, 'name': text, 'sku': text, 'price': random.randint(100, 1000) / 10.0}
                    yield text, item

        spider = TestSpider('amazon.com')

        mock_items = [
            {
                'identifier': 'id1:s_id1',
                'name': 'name1'
            },
            {
                'identifier': 'id1:s_id2',
                'name': 'name2'
            },
            {
                'identifier': 'id2:s_id2',
                'name': 'name3'
            },
            {
                'identifier': 'id3:s_id2',
                'name': 'name3'
            }
        ]
        mock_reviews = {
            'id1': ['review1', 'review2'],
            'id2': ['review3']
        }
        spider.collected_items = mock_items[:]
        spider.collected_reviews = mock_reviews.copy()

        results = list(spider.process_collected_products())

        self.assertEqual(len(results), len(mock_items))
        for item in results:
            self.assertIn(item, mock_items)
            real_identifier = item['identifier'].split(':')[-2]
            if real_identifier in mock_reviews:
                self.assertIn('metadata', item.keys())
                self.assertIn('reviews', item['metadata'])
                self.assertEqual(len(item['metadata']['reviews']), len(mock_reviews[real_identifier]))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertTrue(spider.processed_items)

    def test_process_collected_products_add_reviews_to_products_once_per_id(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            collect_reviews = True
            all_sellers = True
            reviews_once_per_product_without_dealer = True

            def get_search_query_generator(self):
                random.seed()
                for text in ["Lego 123"]:
                    item = {'identifier': text, 'name': text, 'sku': text, 'price': random.randint(100, 1000) / 10.0}
                    yield text, item

        spider = TestSpider('amazon.com')

        mock_items = [
            {
                'identifier': 'id1:s_id1',
                'name': 'name1'
            },
            {
                'identifier': 'id1:s_id2',
                'name': 'name2'
            },
            {
                'identifier': 'id2:s_id2',
                'name': 'name3'
            },
            {
                'identifier': 'id3:s_id2',
                'name': 'name3'
            }
        ]
        mock_reviews = {
            'id1': ['review1', 'review2'],
            'id2': ['review3']
        }
        spider.collected_items = mock_items[:]
        spider.collected_reviews = mock_reviews.copy()

        results = list(spider.process_collected_products())

        products = [x for x in results if x['identifier'].startswith('id1:')]

        self.assertEqual(len(products), 2)

        non_emtpy_reviews = [x for x in products if 'metadata' in x and 'reviews' in x['metadata'] and
                                                    len(x['metadata']['reviews']) > 0]

        self.assertEqual(len(non_emtpy_reviews), 1)

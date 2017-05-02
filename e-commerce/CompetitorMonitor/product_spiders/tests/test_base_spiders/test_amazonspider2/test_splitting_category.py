# -*- coding: utf-8 -*-
import urlparse as up
import unittest

from scrapy.http import Request, Response

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider


class TestAmazonSpiderSearchProcess(unittest.TestCase):
    def test_initial_split(self):
        mock_request = Request('http://amazon.com/asd/qwe/')
        mock_response = Response(mock_request.url, request=mock_request)
        mock_search_results = {}

        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = 'category'
            amazon_direct = True

        spider = TestSpider('amazon.com')

        res = spider.get_subrequests_for_search_results(mock_response, mock_search_results)

        self.assertEqual(len(res), 3)

        self.assertEqual(up.parse_qs(up.urlparse(res[0].url).query)['low-price'][0], 'None')
        self.assertEqual(up.parse_qs(up.urlparse(res[0].url).query)['high-price'][0], '100')

        self.assertEqual(up.parse_qs(up.urlparse(res[1].url).query)['low-price'][0], '100')
        self.assertEqual(up.parse_qs(up.urlparse(res[1].url).query)['high-price'][0], '1000')

        self.assertEqual(up.parse_qs(up.urlparse(res[2].url).query)['low-price'][0], '1000')
        self.assertEqual(up.parse_qs(up.urlparse(res[2].url).query)['high-price'][0], 'None')

    def test_second_split_of_first_req(self):
        mock_request = Request('http://amazon.com/asd/qwe/')
        mock_response = Response(mock_request.url, request=mock_request)
        mock_search_results = {}

        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = 'category'
            amazon_direct = True

        spider = TestSpider('amazon.com')

        res = spider.get_subrequests_for_search_results(mock_response, mock_search_results)

        mock_request = res[0]
        mock_response = Response(mock_request.url, request=mock_request)

        mock_search_results = {
            'products': ['<something>' * 24],
            'results_count': 3000
        }

        res = spider.get_subrequests_for_search_results(mock_response, mock_search_results)

        self.assertNotIn('low-price', up.parse_qs(up.urlparse(res[0].url).query))

    def test_should_stop_on_high_price_1_or_less(self):
        mock_request = Request('http://amazon.com/asd/qwe/?high-price=1')
        mock_request.meta['subrequests'] = {
            'low-price': None,
            'high-price': 1,
        }
        mock_response = Response(mock_request.url, request=mock_request)
        mock_search_results = {
            'products': ['<something>' * 24],
            'results_count': 3000
        }

        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = 'category'
            amazon_direct = True

        spider = TestSpider('amazon.com')

        res = spider.get_subrequests_for_search_results(mock_response, mock_search_results)

        self.assertEqual(len(res), 0)

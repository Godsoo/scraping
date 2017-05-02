__author__ = 'juraseg'
import urlparse as up
from itertools import combinations
from unittest import TestCase

from product_spiders.base_spiders.amazonspider2 import (
    BaseAmazonSpider,
)

from product_spiders.base_spiders.amazonspider2.amazonspider import get_base_identifier

from product_spiders.tests.test_base_spiders.test_amazonspider2.base_spider_test_case import AmazonBaseTestCase


class TestAmazonSpiderCheckNumberOfResults(AmazonBaseTestCase):
    """
    General tests of `check_number_of_results_fits` method
    """

    def _get_spider(self, mock_scraper, spider_type='search'):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = spider_type
            amazon_direct = True
            domain = 'amazon.com'

            def _collect_best_match(self, item, search_string):
                self.collected_items.append(item)

        spider = TestSpider()
        spider.scraper = mock_scraper
        spider.collected_items = []
        spider.current_search_item = None
        spider.current_search = None

        return spider

    def test_true_on_non_category_type(self):
        for spider_type in ['search', 'asins']:
            scraper = self._get_mock_scraper_products_list(
                products=True,
                results_count=1000000)
            spider = self._get_spider(scraper, spider_type)

            mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {'search_string': 'item'})

            res = spider.check_number_of_results_fits(scraper.scrape_search_results_page(mock_response))

            self.assertTrue(res)

    def test_false_if_category_type_and_number_of_pages_to_parse_bigger_than_400(self):
        results_count = len(self._get_mock_items()) * 400 + 1
        scraper = self._get_mock_scraper_products_list(
            products=True,
            results_count=results_count)
        spider = self._get_spider(scraper, 'category')

        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {})

        res = spider.check_number_of_results_fits(scraper.scrape_search_results_page(mock_response))

        self.assertFalse(res)

    def test_true_if_category_and_no_products(self):
        results_count = 1000000
        scraper = self._get_mock_scraper_products_list(
            products=False,
            results_count=results_count)
        spider = self._get_spider(scraper, 'category')

        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {})

        res = spider.check_number_of_results_fits(scraper.scrape_search_results_page(mock_response))

        self.assertTrue(res)


class TestGetSubrequestsForSearch(AmazonBaseTestCase):
    """
    General tests of `get_subrequests_for_search_results` method
    """

    def _get_spider(self, mock_scraper, spider_type='search'):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = spider_type
            amazon_direct = True
            domain = 'amazon.com'

            def _collect_best_match(self, item, search_string):
                self.collected_items.append(item)

        spider = TestSpider()
        spider.scraper = mock_scraper
        spider.collected_items = []
        spider.current_search_item = None
        spider.current_search = None

        return spider

    def test_initial_creates_3_requests(self):
        results_count = len(self._get_mock_items()) * 400 + 1
        scraper = self._get_mock_scraper_products_list(
            products=True,
            results_count=results_count)
        spider = self._get_spider(scraper, 'category')

        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {})

        requests = spider.get_subrequests_for_search_results(
            mock_response,
            spider.scraper.scrape_search_results_page(mock_response))

        # in format: (low-price, high-price), None means that param should be absent
        expected_params = [
            (None, 100),
            (100, 1000),
            (1000, None)
        ]

        self.assertEqual(len(expected_params), len(requests))

        for req in requests:
            parsed_url = up.urlparse(req.url)
            parsed_query = up.parse_qs(parsed_url.query)
            low_price = parsed_query.get('low-price')[0]
            high_price = parsed_query.get('high-price')[0]
            low_price = int(low_price) if low_price != 'None' else None
            high_price = int(high_price) if high_price != 'None' else None
            self.assertIn((low_price, high_price), expected_params)

            self.assertIn('x', parsed_query)
            self.assertIn('y', parsed_query)

            self.assertIn('subrequests', req.meta)
            low_price = req.meta['subrequests']['low-price']
            high_price = req.meta['subrequests']['high-price']
            self.assertIn((low_price, high_price), expected_params)

    def test_subsequent_splits_products(self):
        # should split to three requests as number of products is twice as possible for one request

        results_count = int(len(self._get_mock_items()) * 400 * 1.9)
        scraper = self._get_mock_scraper_products_list(
            products=True,
            results_count=results_count)
        spider = self._get_spider(scraper, 'category')

        low_price = None
        high_price = 100
        meta = {
            'subrequests': {
                'low-price': low_price,
                'high-price': high_price
            }
        }
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, meta)

        requests = spider.get_subrequests_for_search_results(
            mock_response,
            spider.scraper.scrape_search_results_page(mock_response))

        # in format: (low-price, high-price), None means that param should be absent
        expected_params = [
            (None, 50),
            (50, 100)
        ]

        self.assertEqual(len(expected_params), len(requests))

        for req in requests:
            parsed_url = up.urlparse(req.url)
            parsed_query = up.parse_qs(parsed_url.query)
            low_price = parsed_query.get('low-price')[0]
            high_price = parsed_query.get('high-price')[0]
            low_price = int(low_price) if low_price != 'None' else None
            high_price = int(high_price) if high_price != 'None' else None
            self.assertIn((low_price, high_price), expected_params)

            self.assertIn('x', parsed_query)
            self.assertIn('y', parsed_query)

            self.assertIn('subrequests', req.meta)
            low_price = req.meta['subrequests']['low-price']
            high_price = req.meta['subrequests']['high-price']
            self.assertIn((low_price, high_price), expected_params)


class TestAuxiliaryFunctions(TestCase):
    def test_get_base_identifier(self):
        expected_results = [
            ('asd:qwe', 'asd'),
            (':asd:qwe', 'asd'),
            ('asd', 'asd'),
            (':asd', 'asd'),
            (':asd:', 'asd'),
            (':', ':'),
            ('', '')
        ]

        for identifier, expected_result in expected_results:
            res = get_base_identifier(identifier)
            self.assertEqual(res, expected_result,
                             'Expected "%s", got "%s"' % (expected_result, res))


class TestTypeChecking(TestCase):
    def test_checking_one_type(self):
        valid_types = ['asins', 'search', 'category']
        invalid_types = ['asin', 'searches', 'categories', 'categori', 'asd', 'qwe', 'zxc', '11232']

        for t in valid_types:
            self.assertTrue(BaseAmazonSpider._is_type_valid(t))

        for t in invalid_types:
            self.assertFalse(BaseAmazonSpider._is_type_valid(t))

    def test_spider_type_str_checking(self):
        valid_types = ['asins', 'search', 'category']
        valid_types_unicode = [u'asins', u'search', u'category']

        for t in valid_types:
            self.assertTrue(BaseAmazonSpider._is_spider_type_valid(t))

        for t in valid_types_unicode:
            self.assertTrue(BaseAmazonSpider._is_spider_type_valid(t))

    def test_spider_type_list_checking(self):
        valid_types = ['asins', 'search', 'category']
        invalid_types = ['asin', 'searches', 'categories', 'categori', 'asd', 'qwe', 'zxc', '11232']

        for list_size in xrange(1, len(valid_types) + 1):
            for spider_type in self._gen_spider_type_lists(list_size, valid_types):
                self.assertTrue(BaseAmazonSpider._is_spider_type_valid(spider_type))

                for t in invalid_types:
                    spider_type.append(t)

                    self.assertFalse(BaseAmazonSpider._is_spider_type_valid(spider_type))

    def _gen_spider_type_lists(self, size, valid_types):
        return map(list, combinations(valid_types, size))

    def test_spider_type_list_duplicates_not_allowed(self):
        spider_type = ['asins', 'search', 'search']

        self.assertFalse(BaseAmazonSpider._is_spider_type_valid(spider_type))

    def test_spider_type_invalid_data_type_raises(self):
        spider_type = ('asins', 'search')

        self.assertRaises(TypeError, BaseAmazonSpider._is_spider_type_valid, spider_type=spider_type)

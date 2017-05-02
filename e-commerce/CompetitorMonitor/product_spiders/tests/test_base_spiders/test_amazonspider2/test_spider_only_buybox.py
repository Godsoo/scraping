# -*- coding: utf-8 -*-
import mock

from product_spiders.tests.test_base_spiders.test_amazonspider2.base_spider_test_case import AmazonBaseTestCase
from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider


class TestAmazonSpiderBuyBox(AmazonBaseTestCase):
    """
    Test for cases when only_buybox is True
    """
    def _get_spider(self, mock_scraper, spider_type='search'):

        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            only_buybox = True
            domain = 'amazon.com'
            type = spider_type

            def _collect_best_match(self, item, search_string):
                self.collected_items.append(item)

        spider = TestSpider()
        spider.scraper = mock_scraper
        spider.collected_items = []
        spider.current_search_item = {'name': 'item', 'price': '1.5'}
        spider.current_search = 'item'

        return spider

    def test_parse_products_list_redirects_to_product_details_if_match(self):
        spider = self._get_spider(self._get_mock_scraper_products_list())
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {'search_string': 'item'})

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), len(self._get_mock_items()))

        expected_urls = [x['url'] for x in self._get_mock_items()]

        for request in results:
            self.assertEqual(request.callback, spider.parse_product)
            self.assertIn(request.url, expected_urls)
            self.assertFalse(request.meta.get('check_match', False))

    def test_parse_products_list_collects_if_match_and_dealer_not_mandatory(self):
        spider = self._get_spider(self._get_mock_scraper_products_list())
        spider.dealer_is_mandatory = False
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {'search_string': 'item'})

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(spider.collected_items), len(self._get_mock_items()))
        self.assertEqual(len(results), 0)

        expected_identifiers = [':' + x['identifier'] for x in self._get_mock_items()]

        for item in spider.collected_items:
            self.assertIn(item['identifier'], expected_identifiers)

    def test_parse_products_list_redirects_to_product_details_if_from_list_disabled(self):
        spider = self._get_spider(self._get_mock_scraper_products_list())
        spider.dealer_is_mandatory = False
        spider.match = mock.MagicMock(return_value=True)
        spider.collect_products_from_list = False
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {'search_string': 'item'})

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), len(self._get_mock_items()))

        expected_urls = [x['url'] for x in self._get_mock_items()]

        for request in results:
            self.assertEqual(request.callback, spider.parse_product)
            self.assertIn(request.url, expected_urls)
            self.assertTrue(request.meta.get('check_match', True))

    def test_parse_products_list_redirects_to_product_details_if_no_match_and_enabled(self):
        spider = self._get_spider(self._get_mock_scraper_products_list())
        spider.match = mock.MagicMock(return_value=False)
        spider.try_match_product_details_if_product_list_not_matches = True
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {'search_string': 'item'})

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), len(self._get_mock_items()))

        expected_urls = [x['url'] for x in self._get_mock_items()]

        for request in results:
            self.assertEqual(request.callback, spider.parse_product)
            self.assertIn(request.url, expected_urls)
            self.assertTrue(request.meta['check_match'])

    def test_parse_product_details_returns_nothing_if_not_match(self):
        spider = self._get_spider(self._get_mock_scraper_product_details())
        spider.parse_options = True
        spider.match = mock.MagicMock(return_value=False)
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            meta={
                'search_string': spider.current_search,
                'search_item': spider.current_search_item,
                'check_match': True
            }
        )

        results = list(spider.parse_product(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), 0)

    def test_parse_product_details_parses_options_if_already_matched(self):
        spider = self._get_spider(self._get_mock_scraper_product_details())
        spider.parse_options = True
        spider.match = mock.MagicMock(return_value=False)
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            meta={
                'search_string': spider.current_search,
                'search_item': spider.current_search_item,
                'check_match': False
            }
        )

        results = list(spider.parse_product(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), len(self._get_mock_item()['options']))

        expected_urls = [x['url'] for x in self._get_mock_item()['options']]

        for request in results:
            self.assertEqual(request.callback, spider.parse_product)
            self.assertIn(request.url, expected_urls)
            self.assertFalse(request.meta.get('check_match', False))

    def test_parse_product_details_collects_product_if_options_parsed(self):
        spider = self._get_spider(self._get_mock_scraper_product_details())
        spider.parse_options = True
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            meta={
                'search_string': spider.current_search,
                'search_item': spider.current_search_item,
                'check_match': False,
                'parse_options': False
            }
        )

        results = list(spider.parse_product(mock_response))

        self.assertEqual(len(spider.collected_items), 1)
        self.assertEqual(len(results), 0)
        self.assertEqual(spider.collected_items[0]['identifier'], ':' + self._get_mock_item()['identifier'])
        self.assertEqual(spider.collected_items[0]['dealer'], self._get_mock_item()['vendor'])

    def test_parse_product_details_does_not_collects_product_if_asin_does_not_match_url_asin_type(self):
        mock_item = self._get_mock_item(vendor=False)
        # ASINs type skips product when collected asin does not match url asin
        asin = mock_item['asin']
        url_asin = asin + '_diff'
        mock_item['url'] = 'http://asdqwe.zxc/alskdj/dp/%s/alsdoqiwu' % url_asin

        mock_scraper = self._get_mock_scraper_product_details()
        mock_scraper.set_product_details(mock_item)

        spider = self._get_spider(mock_scraper, spider_type='asins')
        spider.parse_options = True
        spider.match = mock.MagicMock(return_value=False)
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            {
                'search_string': spider.current_search,
                'search_item': spider.current_search_item,
                'check_match': False,
                'parse_options': False
            })

        results = list(spider.parse_product(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), 0)

    def test_parse_product_details_uses_collect_amazon_direct(self):
        spider = self._get_spider(self._get_mock_scraper_product_details())
        spider.parse_options = True
        spider.match = mock.MagicMock(return_value=False)
        spider._collect_buybox = mock.MagicMock()
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            {
                'search_string': spider.current_search,
                'search_item': spider.current_search_item,
                'check_match': False,
                'parse_options': False
            })

        self.assertFalse(spider._collect_buybox.called)
        results = list(spider.parse_product(mock_response))
        self.assertTrue(spider._collect_buybox.called)

    def test_parse_product_details_not_collects_product_if_no_vendor(self):
        spider = self._get_spider(self._get_mock_scraper_product_details(vendor=False))
        spider.parse_options = True
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            meta={
                'search_string': spider.current_search,
                'search_item': spider.current_search_item,
                'check_match': False,
                'parse_options': False
            }
        )

        results = list(spider.parse_product(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), 0)

    def test_parse_product_details_collects_product_if_no_vendor_and_collect_no_dealer_enabled(self):
        spider = self._get_spider(self._get_mock_scraper_product_details(vendor=False))
        spider.parse_options = True
        spider.collect_products_with_no_dealer = True
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            meta={
                'search_string': spider.current_search,
                'search_item': spider.current_search_item,
                'check_match': False,
                'parse_options': False
            }
        )

        results = list(spider.parse_product(mock_response))

        self.assertEqual(len(spider.collected_items), 1)
        self.assertEqual(len(results), 0)

    def test_parse_product_details_not_collects_product_if_vendor_is_excluded(self):
        spider = self._get_spider(self._get_mock_scraper_product_details())
        spider.exclude_sellers = [self._get_mock_item()['vendor']]
        spider.parse_options = True
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            meta={
                'search_string': spider.current_search,
                'search_item': spider.current_search_item,
                'check_match': False,
                'parse_options': False
            }
        )

        results = list(spider.parse_product(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), 0)

    def test_parse_product_details_not_collects_product_if_vendor_not_included(self):
        spider = self._get_spider(self._get_mock_scraper_product_details())
        spider.sellers = ['QWE']
        spider.parse_options = True
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            meta={
                'search_string': spider.current_search,
                'search_item': spider.current_search_item,
                'check_match': False,
                'parse_options': False
            }
        )

        results = list(spider.parse_product(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), 0)

    def test_parse_product_details_collects_product_if_vendor_is_included(self):
        spider = self._get_spider(self._get_mock_scraper_product_details())
        spider.sellers = ['ASD']
        spider.parse_options = True
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            meta={
                'search_string': spider.current_search,
                'search_item': spider.current_search_item,
                'check_match': False,
                'parse_options': False
            }
        )

        results = list(spider.parse_product(mock_response))

        self.assertEqual(len(spider.collected_items), 1)
        self.assertEqual(len(results), 0)

    def test_parse_product_details_redirects_to_reviews_if_options_parsed(self):
        spider = self._get_spider(self._get_mock_scraper_product_details())
        spider.parse_options = True
        spider.collect_reviews = True
        spider.reviews_only_matched = False
        spider.match = mock.MagicMock(return_value=False)
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            meta={
                'search_string': spider.current_search,
                'search_item': spider.current_search_item,
                'check_match': False,
                'parse_options': False
            }
        )

        results = list(spider.parse_product(mock_response))

        # product is collected
        self.assertEqual(len(spider.collected_items), 1)
        self.assertEqual(len(results), 1)

        mock_item = self._get_mock_item()

        result = results[0]
        self.assertEqual(result.callback, spider.parse_reviews)
        self.assertEqual(result.url, mock_item['reviews_url'])
        mock_item['vendor'] = mock_item['vendor']
        self.assertEqual(result.meta['found_item'], mock_item)

    def test_parse_product_details_not_redirects_to_reviews_if_asin_does_not_match_url_asin_type(self):
        mock_item = self._get_mock_item(vendor=False)
        # ASINs type skips product when collected asin does not match url asin
        asin = mock_item['asin']
        url_asin = asin + '_diff'
        mock_item['url'] = 'http://asdqwe.zxc/alskdj/dp/%s/alsdoqiwu' % url_asin

        mock_scraper = self._get_mock_scraper_product_details()
        mock_scraper.set_product_details(mock_item)

        spider = self._get_spider(mock_scraper, spider_type='asins')
        spider.parse_options = True
        spider.collect_reviews = True
        spider.match = mock.MagicMock(return_value=False)
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            {
                'search_string': spider.current_search,
                'search_item': spider.current_search_item,
                'check_match': False,
                'parse_options': False
            })

        results = list(spider.parse_product(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), 0)
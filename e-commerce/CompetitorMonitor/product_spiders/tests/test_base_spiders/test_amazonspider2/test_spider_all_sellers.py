# -*- coding: utf-8 -*-
import mock

from product_spiders.tests.test_base_spiders.test_amazonspider2.base_spider_test_case import AmazonBaseTestCase
from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider, AmazonProduct


class TestAmazonSpiderAllSellers(AmazonBaseTestCase):
    def _get_spider(self, mock_scraper, spider_type='search'):

        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = spider_type
            all_sellers = True
            collect_new_products = True
            domain = 'amazon.com'

            def _collect_best_match(self, item, search_string):
                self.collected_items.append(item)

        spider = TestSpider()
        spider.scraper = mock_scraper
        spider.collected_items = []
        if spider.type == 'search':
            spider.current_search_item = {'name': 'item', 'price': '1.5'}
            spider.current_search = 'item'

        return spider

    def test_parse_products_list_redirects_to_product_details_if_from_list_disabled(self):
        for spider_type in ['search', 'asins', 'category']:
            spider = self._get_spider(self._get_mock_scraper_products_list(), spider_type=spider_type)
            spider.collect_products_from_list = False
            meta = {}
            if spider.type == 'search':
                meta.update({
                    'search_string': 'item'
                })
            mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, meta)

            results = list(spider.parse_product_list(mock_response))

            self.assertEqual(len(spider.collected_items), 0)
            self.assertEqual(len(results), len(self._get_mock_items()))

            expected_urls = [x['url'] for x in self._get_mock_items()]

            for request in results:
                self.assertEqual(request.callback, spider.parse_product)
                self.assertIn(request.url, expected_urls)
                self.assertTrue(request.meta.get('check_match', True))

    def test_parse_products_list_redirects_to_mbc_if_match(self):
        for spider_type in ['search', 'asins', 'category']:
            spider = self._get_spider(self._get_mock_scraper_products_list(), spider_type=spider_type)
            spider.match = mock.MagicMock(return_value=True)
            meta = {}
            if spider.type == 'search':
                meta.update({
                    'search_string': 'item'
                })
            mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, meta)

            results = list(spider.parse_product_list(mock_response))

            self.assertEqual(len(spider.collected_items), 0)
            self.assertEqual(len(results), len(self._get_mock_items()))

            expected_urls = [x['mbc_list_url_new'] for x in self._get_mock_items()]

            for request in results:
                self.assertEqual(request.callback, spider.parse_mbc_list)
                self.assertIn(request.url, expected_urls)
                self.assertFalse(request.meta.get('check_match', False))

    def test_parse_products_list_redirects_to_product_details_if_match_and_options(self):
        for spider_type in ['search', 'asins', 'category']:
            spider = self._get_spider(self._get_mock_scraper_products_list(), spider_type=spider_type)
            spider.parse_options = True
            spider.match = mock.MagicMock(return_value=True)

            meta = {}
            if spider.type == 'search':
                meta.update({
                    'search_string': 'item'
                })
            mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, meta)

            results = list(spider.parse_product_list(mock_response))

            self.assertEqual(len(spider.collected_items), 0)
            self.assertEqual(len(results), len(self._get_mock_items()))

            expected_urls = [x['url'] for x in self._get_mock_items()]

            for request in results:
                self.assertEqual(request.callback, spider.parse_product)
                self.assertIn(request.url, expected_urls)
                self.assertFalse(request.meta.get('check_match', False))

    def test_parse_products_list_redirects_to_product_details_if_no_match_but_basic_match(self):
        for spider_type in ['search']:  # makes sense only for search type
            spider = self._get_spider(self._get_mock_scraper_products_list(), spider_type=spider_type)
            spider.basic_match = mock.MagicMock(return_value=True)
            spider.match = mock.MagicMock(return_value=False)
            meta = {}
            if spider.type == 'search':
                meta.update({
                    'search_string': 'item'
                })
            mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, meta)

            results = list(spider.parse_product_list(mock_response))

            self.assertEqual(len(spider.collected_items), 0)
            self.assertEqual(len(results), len(self._get_mock_items()))

            expected_urls = [x['url'] for x in self._get_mock_items()]

            for request in results:
                self.assertEqual(request.callback, spider.parse_product)
                self.assertIn(request.url, expected_urls)
                self.assertTrue(request.meta['check_match'])

    def test_parse_product_details_returns_nothing_if_not_match(self):
        for spider_type in ['search']:  # makes sense only for search type
            spider = self._get_spider(self._get_mock_scraper_product_details(), spider_type=spider_type)
            spider.parse_options = True
            spider.match = mock.MagicMock(return_value=False)
            meta = {
                'check_match': True
            }
            if spider.type == 'search':
                meta.update({
                    'search_string': spider.current_search,
                    'search_item': spider.current_search_item,
                })
            mock_response = self._get_mock_response(spider.domain, spider.parse_product, meta)

            results = list(spider.parse_product(mock_response))

            self.assertEqual(len(spider.collected_items), 0)
            self.assertEqual(len(results), 0)

    def test_parse_product_details_parses_options_if_already_matched(self):
        for spider_type in ['search']:  # makes sense only for search type
            spider = self._get_spider(self._get_mock_scraper_product_details(), spider_type=spider_type)
            spider.parse_options = True
            spider.match = mock.MagicMock(return_value=False)
            meta = {
                'check_match': False
            }
            if spider.type == 'search':
                meta.update({
                    'search_string': spider.current_search,
                    'search_item': spider.current_search_item,
                })
            mock_response = self._get_mock_response(spider.domain, spider.parse_product, meta)

            results = list(spider.parse_product(mock_response))

            self.assertEqual(len(spider.collected_items), 0)
            self.assertEqual(len(results), len(self._get_mock_item()['options']))

            expected_urls = [x['url'] for x in self._get_mock_item()['options']]

            for request in results:
                self.assertEqual(request.callback, spider.parse_product)
                self.assertIn(request.url, expected_urls)
                self.assertFalse(request.meta.get('check_match', False))

    def test_parse_product_details_redirects_to_mbc_if_options_parsed(self):
        for spider_type in ['search', 'asins', 'category']:
            mock_item = self._get_mock_item()

            # ASINs type skips product when collected asin does not match url asin
            asin = mock_item['asin']
            mock_item['url'] = 'http://asdqwe.zxc/alskdj/dp/%s/alsdoqiwu' % asin

            mock_scraper = self._get_mock_scraper_product_details()
            mock_scraper.set_product_details(mock_item)

            spider = self._get_spider(mock_scraper, spider_type=spider_type)
            spider.parse_options = True
            spider.match = mock.MagicMock(return_value=True)
            meta = {
                'check_match': False,
                'parse_options': False
            }
            if spider.type == 'search':
                meta.update({
                    'search_string': spider.current_search,
                    'search_item': spider.current_search_item,
                })
            mock_response = self._get_mock_response(spider.domain, spider.parse_product, meta=meta)

            results = list(spider.parse_product(mock_response))

            self.assertEqual(len(spider.collected_items), 0)
            self.assertEqual(len(results), 1)
            result = results[0]
            self.assertEqual(result.callback, spider.parse_mbc_list)
            self.assertEqual(result.url, self._get_mock_item()['mbc_list_url_new'])

    def test_parse_product_details_collects_product_if_options_parsed_and_no_mbc(self):
        for spider_type in ['search', 'asins']:
            mock_item = self._get_mock_item()
            del(mock_item['mbc_list_url_new'])
            del(mock_item['mbc_list_url_used'])

            # ASINs type skips product when collected asin does not match url asin
            asin = mock_item['asin']
            mock_item['url'] = 'http://asdqwe.zxc/alskdj/dp/%s/alsdoqiwu' % asin

            mock_scraper = self._get_mock_scraper_product_details()
            mock_scraper.set_product_details(mock_item)
            spider = self._get_spider(mock_scraper, spider_type=spider_type)
            spider.parse_options = True
            spider.collect_reviews = False
            spider.match = mock.MagicMock(return_value=True)
            meta = {
                'check_match': False,
                'parse_options': False
            }
            if spider.type == 'search':
                meta.update({
                    'search_string': spider.current_search,
                    'search_item': spider.current_search_item,
                })
            mock_response = self._get_mock_response(spider.domain, spider.parse_product, meta=meta)

            results = list(spider.parse_product(mock_response))

            self.assertEqual(len(results), 0)
            self.assertEqual(len(spider.collected_items), 1)

    def test_parse_product_details_does_not_collects_product_if_asin_does_not_match_url_asin_mode(self):
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

    def test_parse_product_details_collects_product_if_options_parsed_and_no_mbc_category_type(self):
        for spider_type in ['category']:
            mock_item = self._get_mock_item()
            del(mock_item['mbc_list_url_new'])
            del(mock_item['mbc_list_url_used'])
            mock_scraper = self._get_mock_scraper_product_details()
            mock_scraper.set_product_details(mock_item)
            spider = self._get_spider(mock_scraper, spider_type=spider_type)
            spider.parse_options = True
            spider.collect_reviews = False
            spider.match = mock.MagicMock(return_value=True)
            meta = {
                'check_match': False,
                'parse_options': False
            }
            if spider.type == 'search':
                meta.update({
                    'search_string': spider.current_search,
                    'search_item': spider.current_search_item,
                })
            mock_response = self._get_mock_response(spider.domain, spider.parse_product, meta=meta)

            results = list(spider.parse_product(mock_response))
            items = [x for x in results if isinstance(x, AmazonProduct)]
            request = [x for x in results if not isinstance(x, AmazonProduct)]

            self.assertEqual(len(items), 1)
            self.assertEqual(len(request), 0)

    def test_parse_product_details_redirects_to_reviews_if_options_parsed_and_no_mbc_and_reviews_enabled(self):
        for spider_type in ['search', 'asins', 'category']:
            mock_item = self._get_mock_item()
            del(mock_item['mbc_list_url_new'])
            del(mock_item['mbc_list_url_used'])

            # ASINs type skips product when collected asin does not match url asin
            asin = mock_item['asin']
            mock_item['url'] = 'http://asdqwe.zxc/alskdj/dp/%s/alsdoqiwu' % asin

            mock_scraper = self._get_mock_scraper_product_details()
            mock_scraper.set_product_details(mock_item)
            spider = self._get_spider(mock_scraper, spider_type=spider_type)
            spider.parse_options = True
            spider.collect_reviews = True
            spider.reviews_only_matched = False
            spider.match = mock.MagicMock(return_value=True)
            meta = {
                'check_match': False,
                'parse_options': False
            }
            if spider.type == 'search':
                meta.update({
                    'search_string': spider.current_search,
                    'search_item': spider.current_search_item,
                })
            mock_response = self._get_mock_response(spider.domain, spider.parse_product, meta=meta)

            results = list(spider.parse_product(mock_response))

            # product is still collected
            self.assertEqual(len(spider.collected_items), 1)
            self.assertEqual(len(results), 1)
            result = results[0]
            self.assertEqual(result.callback, spider.parse_reviews)


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

    def test_parse_product_details_not_collects_product_if_no_vendor(self):
        for spider_type in ['search', 'asins', 'category']:
            mock_item = self._get_mock_item(vendor=False)
            del(mock_item['mbc_list_url_new'])
            del(mock_item['mbc_list_url_used'])

            # ASINs type skips product when collected asin does not match url asin
            asin = mock_item['asin']
            mock_item['url'] = 'http://asdqwe.zxc/alskdj/dp/%s/alsdoqiwu' % asin

            mock_scraper = self._get_mock_scraper_product_details()
            mock_scraper.set_product_details(mock_item)
            spider = self._get_spider(mock_scraper, spider_type=spider_type)
            spider.parse_options = True
            spider.match = mock.MagicMock(return_value=True)
            meta = {
                'check_match': False,
                'parse_options': False
            }
            if spider.type == 'search':
                meta.update({
                    'search_string': spider.current_search,
                    'search_item': spider.current_search_item,
                })
            mock_response = self._get_mock_response(spider.domain, spider.parse_product, meta=meta)

            results = list(spider.parse_product(mock_response))

            self.assertEqual(len(spider.collected_items), 0)
            self.assertEqual(len(results), 0)

    def test_parse_product_details_collects_product_if_no_vendor_and_collect_no_dealer_enabled(self):
        for spider_type in ['search', 'asins']:
            mock_item = self._get_mock_item(vendor=False)
            del(mock_item['mbc_list_url_new'])
            del(mock_item['mbc_list_url_used'])

            # ASINs type skips product when collected asin does not match url asin
            asin = mock_item['asin']
            mock_item['url'] = 'http://asdqwe.zxc/alskdj/dp/%s/alsdoqiwu' % asin

            mock_scraper = self._get_mock_scraper_product_details()
            mock_scraper.set_product_details(mock_item)
            spider = self._get_spider(mock_scraper, spider_type=spider_type)
            spider.parse_options = True
            spider.collect_products_with_no_dealer = True
            spider.match = mock.MagicMock(return_value=True)
            meta = {
                'check_match': False,
                'parse_options': False
            }
            if spider.type == 'search':
                meta.update({
                    'search_string': spider.current_search,
                    'search_item': spider.current_search_item,
                })
            mock_response = self._get_mock_response(spider.domain, spider.parse_product, meta=meta)

            results = list(spider.parse_product(mock_response))

            self.assertEqual(len(spider.collected_items), 1)
            self.assertEqual(len(results), 0)

    def test_parse_product_details_collects_product_if_no_vendor_and_collect_no_dealer_enabled_category_type(self):
        for spider_type in ['category']:
            mock_item = self._get_mock_item(vendor=False)
            del(mock_item['mbc_list_url_new'])
            del(mock_item['mbc_list_url_used'])
            mock_scraper = self._get_mock_scraper_product_details()
            mock_scraper.set_product_details(mock_item)
            spider = self._get_spider(mock_scraper, spider_type=spider_type)
            spider.parse_options = True
            spider.collect_products_with_no_dealer = True
            spider.match = mock.MagicMock(return_value=True)
            meta = {
                'check_match': False,
                'parse_options': False
            }
            if spider.type == 'search':
                meta.update({
                    'search_string': spider.current_search,
                    'search_item': spider.current_search_item,
                })
            mock_response = self._get_mock_response(spider.domain, spider.parse_product, meta=meta)

            results = list(spider.parse_product(mock_response))
            items = [x for x in results if isinstance(x, AmazonProduct)]
            request = [x for x in results if not isinstance(x, AmazonProduct)]

            self.assertEqual(len(items), 1)
            self.assertEqual(len(request), 0)

    def test_parse_product_details_not_collects_product_if_vendor_is_excluded(self):
        for spider_type in ['search', 'asins', 'category']:
            mock_item = self._get_mock_item()
            del(mock_item['mbc_list_url_new'])
            del(mock_item['mbc_list_url_used'])

            # ASINs type skips product when collected asin does not match url asin
            asin = mock_item['asin']
            mock_item['url'] = 'http://asdqwe.zxc/alskdj/dp/%s/alsdoqiwu' % asin

            mock_scraper = self._get_mock_scraper_product_details()
            mock_scraper.set_product_details(mock_item)
            spider = self._get_spider(mock_scraper, spider_type=spider_type)
            spider.exclude_sellers = [self._get_mock_item()['vendor']]
            spider.parse_options = True
            spider.match = mock.MagicMock(return_value=True)
            meta = {
                'check_match': False,
                'parse_options': False
            }
            if spider.type == 'search':
                meta.update({
                    'search_string': spider.current_search,
                    'search_item': spider.current_search_item,
                })
            mock_response = self._get_mock_response(spider.domain, spider.parse_product, meta=meta)

            results = list(spider.parse_product(mock_response))

            self.assertEqual(len(spider.collected_items), 0)
            self.assertEqual(len(results), 0)

    def test_parse_product_details_not_collects_product_if_vendor_not_included(self):
        for spider_type in ['search', 'asins', 'category']:
            mock_item = self._get_mock_item()
            del(mock_item['mbc_list_url_new'])
            del(mock_item['mbc_list_url_used'])

            # ASINs type skips product when collected asin does not match url asin
            asin = mock_item['asin']
            mock_item['url'] = 'http://asdqwe.zxc/alskdj/dp/%s/alsdoqiwu' % asin

            mock_scraper = self._get_mock_scraper_product_details()
            mock_scraper.set_product_details(mock_item)
            spider = self._get_spider(mock_scraper, spider_type=spider_type)
            spider.sellers = ['QWE']
            spider.parse_options = True
            spider.match = mock.MagicMock(return_value=True)
            meta = {
                'check_match': False,
                'parse_options': False
            }
            if spider.type == 'search':
                meta.update({
                    'search_string': spider.current_search,
                    'search_item': spider.current_search_item,
                })
            mock_response = self._get_mock_response(spider.domain, spider.parse_product, meta=meta)

            results = list(spider.parse_product(mock_response))

            self.assertEqual(len(spider.collected_items), 0)
            self.assertEqual(len(results), 0)

    def test_parse_product_details_collects_product_if_vendor_is_included(self):
        for spider_type in ['search', 'asins']:
            mock_item = self._get_mock_item()
            del(mock_item['mbc_list_url_new'])
            del(mock_item['mbc_list_url_used'])

            # ASINs type skips product when collected asin does not match url asin
            asin = mock_item['asin']
            mock_item['url'] = 'http://asdqwe.zxc/alskdj/dp/%s/alsdoqiwu' % asin

            mock_scraper = self._get_mock_scraper_product_details()
            mock_scraper.set_product_details(mock_item)
            spider = self._get_spider(mock_scraper, spider_type=spider_type)
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

    def test_parse_product_details_collects_product_if_vendor_is_included_category_type(self):
        for spider_type in ['category']:
            mock_item = self._get_mock_item()
            del(mock_item['mbc_list_url_new'])
            del(mock_item['mbc_list_url_used'])
            mock_scraper = self._get_mock_scraper_product_details()
            mock_scraper.set_product_details(mock_item)
            spider = self._get_spider(mock_scraper, spider_type=spider_type)
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
            items = [x for x in results if isinstance(x, AmazonProduct)]
            request = [x for x in results if not isinstance(x, AmazonProduct)]

            self.assertEqual(len(items), 1)
            self.assertEqual(len(request), 0)

    def test_parse_product_details_collects_products_after_mbc_list(self):
        for spider_type in ['search', 'asins']:
            mock_item = self._get_mock_item()

            # ASINs type skips product when collected asin does not match url asin
            asin = mock_item['asin']
            mock_item['url'] = 'http://asdqwe.zxc/alskdj/dp/%s/alsdoqiwu' % asin

            mock_scraper = self._get_mock_scraper_product_details()
            mock_scraper.set_product_details(mock_item)
            spider = self._get_spider(mock_scraper, spider_type=spider_type)
            spider.sellers = ['ASD']
            spider.parse_options = True
            spider.match = mock.MagicMock(return_value=True)
            meta = {
                'check_match': False,
                'parse_options': False,
                'collect_mbc': False,
                'seller_identifier': 'seller_id'
            }
            if spider.type == 'search':
                meta.update({
                    'search_string': spider.current_search,
                    'search_item': spider.current_search_item,
                })
            mock_response = self._get_mock_response(spider.domain, spider.parse_product, meta=meta)

            results = list(spider.parse_product(mock_response))

            self.assertEqual(len(spider.collected_items), 1)
            self.assertEqual(len(results), 0)

            item = spider.collected_items[0]

            self.assertEqual(item['identifier'],
                             ':%s:%s' % (mock_item['identifier'], mock_response.meta['seller_identifier']))

    def test_parse_product_details_collects_products_after_mbc_list_category_type(self):
        for spider_type in ['category']:
            mock_item = self._get_mock_item()
            mock_scraper = self._get_mock_scraper_product_details()
            mock_scraper.set_product_details(mock_item)
            spider = self._get_spider(mock_scraper, spider_type=spider_type)
            spider.sellers = ['ASD']
            spider.parse_options = True
            spider.match = mock.MagicMock(return_value=True)
            meta = {
                'check_match': False,
                'parse_options': False,
                'collect_mbc': False,
                'seller_identifier': 'seller_id'
            }
            if spider.type == 'search':
                meta.update({
                    'search_string': spider.current_search,
                    'search_item': spider.current_search_item,
                })
            mock_response = self._get_mock_response(spider.domain, spider.parse_product, meta=meta)

            results = list(spider.parse_product(mock_response))
            items = [x for x in results if isinstance(x, AmazonProduct)]
            request = [x for x in results if not isinstance(x, AmazonProduct)]

            self.assertEqual(len(items), 1)
            self.assertEqual(len(request), 0)

            item = items[0]

            self.assertEqual(item['identifier'],
                             ':%s:%s' % (mock_item['identifier'], mock_response.meta['seller_identifier']))

    def test_parse_reviews_not_collects_product_after_mbc_list(self):
        for spider_type in ['search', 'asins', 'category']:
            mock_item = self._get_mock_item()
            mock_reviews = self._get_mock_reviews()
            mock_scraper = self._get_mock_scraper_reviews(reviews=True)
            mock_scraper.set_reviews(mock_reviews)
            spider = self._get_spider(mock_scraper, spider_type=spider_type)
            spider.collect_reviews = True
            spider.sellers = ['ASD']
            spider.parse_options = True
            spider.match = mock.MagicMock(return_value=True)
            meta = {
                'found_item': mock_item,
                'collect_product': False
            }
            if spider.type == 'search':
                meta.update({
                    'search_string': spider.current_search,
                    'search_item': spider.current_search_item,
                })
            mock_response = self._get_mock_response_reviews(spider.domain, spider.parse_product, meta=meta)

            list(spider.parse_reviews(mock_response))

            identifier = mock_item['identifier']

            self.assertEqual(len(spider.collected_items), 0)
            self.assertIn(identifier, spider.collected_reviews)
            self.assertEqual(len(spider.collected_reviews[identifier]), len(mock_reviews))

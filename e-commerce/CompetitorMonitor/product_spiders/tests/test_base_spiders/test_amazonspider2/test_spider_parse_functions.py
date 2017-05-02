# -*- coding: utf-8 -*-
import datetime
import json
from urlparse import parse_qsl, urlparse

import mock

from scrapy.http.request import Request
from scrapy.http import HtmlResponse

from product_spiders.base_spiders.amazonspider2 import (
    BaseAmazonSpider,
    AmazonProduct
)
from product_spiders.tests.test_base_spiders.test_amazonspider2.base_spider_test_case import AmazonBaseTestCase, \
    MockScraper


class TestAmazonSpiderParseProductsList(AmazonBaseTestCase):
    """
    General tests of `parse_product_list` method
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
        spider.current_search_item = {'name': 'item', 'price': '1.5'}
        spider.current_search = 'item'

        return spider

    def test_follows_links_to_suggested_search_if_there_are_no_main_products(self):
        spider = self._get_spider(self._get_mock_scraper_products_list(products=False, suggested_urls=True))
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {'search_string': 'item'})

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(results), len(self._get_mock_suggested_search_urls()))
        for url in self._get_mock_suggested_search_urls():
            self.assertIn(url, [x.url for x in results])

    def test_not_follows_links_to_suggested_search_if_already_is_suggested(self):
        spider = self._get_spider(self._get_mock_scraper_products_list(products=False, suggested_urls=True))
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {'search_string': 'item'})

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(results), 1)

        next_request = results[0]
        self.assertFalse(next_request.meta['follow_suggestions'])
        self.assertFalse(next_request.meta['is_main_search'])

        next_response = HtmlResponse(next_request.url, request=next_request)
        results = list(spider.parse_product_list(next_response))

        self.assertEqual(len(results), 0)

    def test_not_follows_links_to_suggested_search_if_disabled(self):
        spider = self._get_spider(self._get_mock_scraper_products_list(products=False, suggested_urls=True))
        spider.try_suggested = False
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {'search_string': 'item'})

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(results), 0)

    def test_follows_next_page_if_main_search(self):
        spider = self._get_spider(self._get_mock_scraper_products_list(products=False, next_url=True))
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list, {'search_string': 'item'})

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(results), 1)

        found_request = results[0]
        self.assertEqual(found_request.url, self._get_mock_next_page_url())
        self.assertEqual(found_request.callback, spider.parse_product_list)
        self.assertEqual(found_request.meta['current_page'], 2)
        self.assertFalse(found_request.meta['follow_suggestions'])
        self.assertTrue(found_request.meta['is_main_search'])

    def test_retains_meta_when_follows_next_page(self):
        spider = self._get_spider(self._get_mock_scraper_products_list(products=False, next_url=True))
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product_list,
            {
                'search_string': 'item',
                'test_value': 'value'
            }
        )

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(results), 1)

        found_request = results[0]
        self.assertEqual(found_request.url, self._get_mock_next_page_url())
        self.assertEqual(found_request.callback, spider.parse_product_list)
        self.assertEqual(found_request.meta['current_page'], 2)
        self.assertFalse(found_request.meta['follow_suggestions'])
        self.assertTrue(found_request.meta['is_main_search'])
        self.assertIn('test_value', found_request.meta.keys())
        self.assertEqual(found_request.meta['test_value'], 'value')

    def test_follows_next_page_if_matched_any(self):
        spider = self._get_spider(self._get_mock_scraper_products_list(products=True, next_url=True))
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list,
                                                {'search_string': 'item', 'is_main_search': False})

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(results), 1)

        found_request = results[0]
        self.assertEqual(found_request.url, self._get_mock_next_page_url())
        self.assertEqual(found_request.callback, spider.parse_product_list)
        self.assertEqual(found_request.meta['current_page'], 2)
        self.assertFalse(found_request.meta['follow_suggestions'])
        self.assertFalse(found_request.meta['is_main_search'])

        mock_items2 = [
            {'name': 'item2', 'price': '1.0', 'identifier': 'item2', 'brand': '', 'image_url': '', 'url': ''}
        ]
        mock_next_page_url = 'http://amazon.com/s/next'
        mock_scraper = MockScraper()
        mock_scraper.set_search_results_suggested_products(mock_items2)
        mock_scraper.set_search_results_next_url(mock_next_page_url)

        spider.scraper = mock_scraper
        spider.collected_items = []
        spider.current_search_item = {'name': 'item', 'price': '1.5'}
        spider.current_search = ['item']

        url = 'http://amazon.com/s/something'
        mock_request = Request(url, callback=spider.parse_product_list,
                               meta={'is_main_search': False, 'search_string': 'item'})
        mock_response = HtmlResponse(url, request=mock_request, body='')
        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(results), 1)

        found_request = results[0]
        self.assertEqual(found_request.url, mock_next_page_url)
        self.assertEqual(found_request.callback, spider.parse_product_list)
        self.assertEqual(found_request.meta['current_page'], 2)
        self.assertFalse(found_request.meta['follow_suggestions'])
        self.assertFalse(found_request.meta['is_main_search'])

    def test_follows_next_page_if_not_main_search_and_not_matched_category_type(self):
        spider = self._get_spider(self._get_mock_scraper_products_list(products=False, next_url=True),
                                  spider_type='category')
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list,
                                                {'search_string': 'item', 'is_main_search': False})

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), 1)

        req = results[0]

        self.assertEqual(req.url, self._get_mock_next_page_url())

    def test_not_follows_next_page_if_not_main_search_and_not_matched(self):
        spider = self._get_spider(self._get_mock_scraper_products_list(products=False, next_url=True))
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list,
                                                {'search_string': 'item', 'is_main_search': False})

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), 0)

    def test_splits_to_subrequests_if_number_of_results_does_not_fit(self):
        spider = self._get_spider(self._get_mock_scraper_products_list(products=True, next_url=True, results_count=100))
        spider.match = mock.MagicMock(return_value=True)
        spider.check_number_of_results_fits = mock.MagicMock(return_value=False)

        mock_req1 = mock.MagicMock()
        mock_req1.url = '1'
        mock_req1.meta = {}
        mock_req2 = mock.MagicMock()
        mock_req2.url = '2'
        mock_req2.meta = {}
        mock_requests = [mock_req1, mock_req2]
        spider.get_subrequests_for_search_results = mock.MagicMock(return_value=mock_requests)

        mock_response = self._get_mock_response(spider.domain, spider.parse_product_list,
                                                {'search_string': 'item', 'is_main_search': False})

        results = list(spider.parse_product_list(mock_response))

        self.assertEqual(len(spider.collected_items), 0)
        self.assertEqual(len(results), len(mock_requests))
        for req in results:
            self.assertIn(req, mock_requests)

        spider.get_subrequests_for_search_results.assert_called_once_with(
            mock_response, spider.scraper.scrape_search_results_page(mock_response), spider._max_pages)


class TestAmazonSpiderParseProductDetails(AmazonBaseTestCase):
    def _get_spider(self, mock_scraper):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            amazon_direct = True
            domain = 'amazon.com'

            def _collect_best_match(self, item, search_string):
                self.collected_items.append(item)

        spider = TestSpider()
        spider.scraper = mock_scraper
        spider.collected_items = []
        spider.current_search_item = {'name': 'item', 'price': '1.5'}
        spider.current_search = 'item'

        return spider

    def test_not_collects_if_options(self):
        spider = self._get_spider(self._get_mock_scraper_product_details())
        spider.parse_options = True
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            meta={
                'search_string': spider.current_search,
                'search_item': spider.current_search_item,
                'check_match': False
            }
        )

        spider.parse_product(mock_response)

        self.assertEqual(len(spider.collected_items), 0)

    def test_not_parses_options_after_they_already_parsed(self):
        # run method to parse options
        spider = self._get_spider(self._get_mock_scraper_product_details())
        spider.parse_options = True
        spider.match = mock.MagicMock(return_value=True)
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

        self.assertEqual(len(results), len(self._get_mock_item()['options']))

        for request in results:
            mock_response = self._make_response_out_of_request(request)

            new_results = list(spider.parse_product(mock_response))

            self.assertEqual(len(new_results), 0)

    def test_raise_when_no_match_func_on_search_type(self):
        # run method to parse options
        spider = self._get_spider(self._get_mock_scraper_product_details())
        spider.parse_options = True

        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            meta={
                'search_string': spider.current_search,
                'search_item': spider.current_search_item,
                'check_match': True
            }
        )

        with self.assertRaises(NotImplementedError):
            list(spider.parse_product(mock_response))

    def test_not_raise_when_no_match_func_on_asin_type(self):
        # run method to parse options
        spider = self._get_spider(self._get_mock_scraper_product_details())
        spider.type = 'asins'
        spider.parse_options = True

        spider.current_search = ''
        spider.current_search_item = {'asin': 'BA123', 'sku': ''}

        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            meta={
                'search_string': spider.current_search,
                'search_item': spider.current_search_item,
                'check_match': True
            }
        )
        list(spider.parse_product(mock_response))

    def test_finds_proper_sku_when_uses_big_site_method(self):
        # run method to parse options
        spider = self._get_spider(self._get_mock_scraper_product_details())
        spider_cls = spider.__class__
        scraper = spider.scraper
        spider = None

        search_item = {'identifier': 'id1', 'name': 'asd', 'price': 1.5, 'sku': 'test_sku', 'url': 'http://url1'}

        # creating big site method spider
        from product_spiders.custom_crawl_methods.bigsitemethod import make_bigsitemethod_spider
        from productspidersweb.models import Spider, CrawlMethod
        spider_model = Spider()
        spider_model.website_id = 123456
        spider_model.crawl_method2 = CrawlMethod()
        spider_model.crawl_method2.params = {'full_crawl_day': 1}
        spider2_cls = make_bigsitemethod_spider(spider_cls, spmdl=spider_model)
        spider2 = spider2_cls()
        spider2.scraper = scraper
        spider2.collected_items = []
        spider2.parse_options = False
        spider2.match = mock.MagicMock(return_value=True)

        mock_response = self._get_mock_response(
            spider2.domain,
            spider2.parse_matches_new_system,
            meta={},
            body=json.dumps({'matches': [search_item]})
        )
        res = list(spider2.parse_matches_new_system(mock_response))

        self.assertEqual(len(res), 1)

        req1 = res[0]

        mock_response = self._make_response_out_of_request(req1)

        results = list(spider2.parse_product(mock_response))

        self.assertEqual(len(results), 0)

        res_item = spider2.collected_items[0]

        self.assertEqual(res_item.get('sku'), search_item['sku'])

    def test_redirects_to_ajax_price_if_no_price_and_ajax_price_url(self):
        spider = self._get_spider(self._get_mock_scraper_product_details(price=False, ajax_price_url=True))
        spider.parse_options = True
        spider.match = mock.MagicMock(return_value=True)
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_product,
            meta={
                'search_string': spider.current_search,
                'search_item': spider.current_search_item,
                'check_match': False
            }
        )

        res = list(spider.parse_product(mock_response))

        self.assertEqual(len(spider.collected_items), 0)

        mock_item = spider.scraper.product_details_results
        req = res[0]

        self.assertEqual(req.url, mock_item['ajax_price_url'])
        self.assertEqual(req.callback, spider.parse_ajax_price)
        self.assertEqual(req.meta['product_info'], mock_item)


class TestAmazonSpiderParseReviews(AmazonBaseTestCase):
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
        if spider.type == 'search':
            spider.current_search_item = {'name': 'item', 'price': '1.5'}
            spider.current_search = 'item'

        return spider

    def test_redirects_to_next_page_if_present(self):
        item = self._get_mock_item()
        for spider_type in ['search', 'asins', 'category']:
            spider = self._get_spider(self._get_mock_scraper_reviews(reviews=True, next_page=True),
                                      spider_type=spider_type)
            meta = {'found_item': item}
            if spider_type == 'search':
                meta['search_string'] = 'item'
            mock_response = self._get_mock_response_reviews(spider.domain, spider.parse_reviews, meta)

            results = list(spider.parse_reviews(mock_response))

            self.assertEqual(len(spider.collected_items), 0)
            self.assertEqual(len(results), 1)

            result = results[0]

            self.assertEqual(result.callback, spider.parse_reviews)
            self.assertEqual(result.url, self._get_mock_reviews_next_page())

    def test_collects_reviews_if_no_next_page(self):
        item = self._get_mock_item()
        for spider_type in ['search', 'asins', 'category']:
            spider = self._get_spider(self._get_mock_scraper_reviews(reviews=True, next_page=False),
                                      spider_type=spider_type)
            meta = {'found_item': item}
            if spider_type == 'search':
                meta['search_string'] = 'item'
            mock_response = self._get_mock_response_reviews(spider.domain, spider.parse_reviews, meta)

            results = list(spider.parse_reviews(mock_response))

            self.assertEqual(len(spider.collected_reviews), 1)
            self.assertEqual(len(results), 0)

            reviews = spider.collected_reviews.values()[0]
            self.assertEqual(len(reviews), len(self._get_mock_reviews()))

    def test_collects_product_if_no_next_page(self):
        item = self._get_mock_item()
        for spider_type in ['search', 'asins', 'category']:
            spider = self._get_spider(self._get_mock_scraper_reviews(reviews=True, next_page=False),
                                      spider_type=spider_type)
            spider.collect_reviews = True
            meta = {'found_item': item}
            if spider_type == 'search':
                meta['search_string'] = 'item'
            mock_response = self._get_mock_response_reviews(spider.domain, spider.parse_reviews, meta)

            results = list(spider.parse_reviews(mock_response))

            # parse_reviews does not collect products anymore
            self.assertEqual(len(spider.collected_items), 0)
            self.assertEqual(len(results), 0)

    def test_joins_reviews_from_different_pages(self):
        item = self._get_mock_item()
        for spider_type in ['search', 'asins', 'category']:
            spider = self._get_spider(self._get_mock_scraper_reviews(reviews=True, next_page=True),
                                      spider_type=spider_type)
            meta = {'found_item': item}
            if spider_type == 'search':
                meta['search_string'] = 'item'
            mock_response = self._get_mock_response_reviews(spider.domain, spider.parse_reviews, meta)

            results = list(spider.parse_reviews(mock_response))

            request = results[0]

            mock_response = self._make_response_out_of_request_reviews(request)
            spider.scraper = self._get_mock_scraper_reviews(reviews=True, next_page=False)
            spider.scraper.set_reviews(self._get_mock_reviews2())
            results = list(spider.parse_reviews(mock_response))

            self.assertEqual(len(spider.collected_reviews), 1)
            self.assertEqual(len(results), 0)

            reviews = spider.collected_reviews.values()[0]
            self.assertEqual(len(reviews), len(self._get_mock_reviews()) + len(self._get_mock_reviews2()))

            expected_review_identifiers = [x['identifier'] for x in self._get_mock_reviews() + self._get_mock_reviews2()]

            for review in reviews:
                self.assertIn(review['review_id'], expected_review_identifiers)

    def test_reformats_date(self):
        item = self._get_mock_item()
        for spider_type in ['search', 'asins', 'category']:
            spider = self._get_spider(self._get_mock_scraper_reviews(reviews=True, next_page=False),
                                      spider_type=spider_type)
            spider.review_date_format = "%d %m %Y"
            meta = {'found_item': item}
            if spider_type == 'search':
                meta['search_string'] = 'item'
            mock_response = self._get_mock_response_reviews(spider.domain, spider.parse_reviews, meta)
            list(spider.parse_reviews(mock_response))

            collected_reviews = spider.collected_reviews
            collected_reviews = collected_reviews[collected_reviews.keys()[0]]

            for review in collected_reviews:
                self.assertEqual(review['date'], datetime.datetime.now().strftime(spider.review_date_format))

    def test_sorts_by_date(self):
        item = self._get_mock_item()
        for spider_type in ['search', 'asins', 'category']:
            spider = self._get_spider(self._get_mock_scraper_reviews(reviews=True, next_page=True),
                                      spider_type=spider_type)
            meta = {'found_item': item}
            if spider_type == 'search':
                meta['search_string'] = 'item'
            mock_response = self._get_mock_response_reviews(spider.domain, spider.parse_reviews, meta)
            mock_response = mock_response.replace(url=mock_response.url.replace('sortBy=bySubmissionDateDescending', ''))

            results = list(spider.parse_reviews(mock_response))

            self.assertEqual(len(spider.collected_items), 0)
            self.assertEqual(len(results), 1)

            result = results[0]

            self.assertEqual(result.callback, spider.parse_reviews)

            url = result.url
            parsed_url = urlparse(url)
            expected_parsed_url = urlparse(url)

            self.assertEqual(parsed_url.hostname, expected_parsed_url.hostname)
            self.assertEqual(parsed_url.path, expected_parsed_url.path)

            parsed_query = dict(parse_qsl(parsed_url.query))

            sorting = parsed_query.get('sortBy', '')
            self.assertEqual(sorting, 'bySubmissionDateDescending')

    def stops_if_reviews_are_older_than_3days_before_prev_crawl(self):
        item = self._get_mock_item()
        for spider_type in ['search', 'asins', 'category']:
            spider = self._get_spider(self._get_mock_scraper_reviews(reviews=True, next_page=True),
                                      spider_type=spider_type)
            meta = {'found_item': item}
            if spider_type == 'search':
                meta['search_string'] = 'item'
            mock_response = self._get_mock_response_reviews(spider.domain, spider.parse_reviews, meta)

            spider.prev_crawl_date = datetime.date.today() - datetime.timedelta(days=1)
            reviews_date = spider.prev_crawl_date - datetime.timedelta(days=4)
            reviews = self._get_mock_reviews()
            for review in reviews:
                review['date'] = reviews_date
            spider.scraper.set_reviews(reviews)

            results = list(spider.parse_reviews(mock_response))

            self.assertEqual(len(spider.collected_items), 0)
            self.assertEqual(len(results), 0)


class TestAmazonSpiderParseMbcList(AmazonBaseTestCase):
    def _get_spider(self, mock_scraper, spider_type='search'):

        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            type = spider_type
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

    def test_collects_products(self):
        for spider_type in ['search', 'asins']:
            spider = self._get_spider(self._get_mock_scraper_mbc(), spider_type=spider_type)
            spider._collect = spider._collect_all
            meta = {
                'check_match': False,
                'parse_options': False
            }
            if spider.type == 'search':
                meta.update({
                'search_string': spider.current_search,
                'search_item': spider.current_search_item
            })
            mock_response = self._get_mock_response(
                spider.domain,
                spider.parse_mbc_list,
                meta=meta
            )

            list(spider.parse_mbc_list(mock_response))

            self.assertEqual(len(spider.collected_items), len(self._get_mock_mbc_list_products()))
            expected_ids = [':' + x['identifier'] + ':' + x['seller_identifier'] for x in self._get_mock_mbc_list_products()]
            for p in spider.collected_items:
                self.assertIn(p['identifier'], expected_ids)

    def test_yields_products_when_type_category(self):
        spider = self._get_spider(self._get_mock_scraper_mbc(), spider_type='category')
        spider._collect = spider._collect_all
        meta = {
            'check_match': False,
            'parse_options': False
        }
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_mbc_list,
            meta=meta
        )

        results = list(spider.parse_mbc_list(mock_response))
        items = [x for x in results if isinstance(x, AmazonProduct)]

        self.assertEqual(len(items), len(self._get_mock_mbc_list_products()))
        expected_ids = [':' + x['identifier'] + ':' + x['seller_identifier'] for x in self._get_mock_mbc_list_products()]
        for p in items:
            self.assertIn(p['identifier'], expected_ids)

    def test_redirects_to_next_page_if_exists(self):
        for spider_type in ['search', 'asins', 'category']:
            spider = self._get_spider(self._get_mock_scraper_mbc(), spider_type=spider_type)
            spider._collect = spider._collect_all
            meta = {
                'check_match': False,
                'parse_options': False
            }
            if spider.type == 'search':
                meta.update({
                'search_string': spider.current_search,
                'search_item': spider.current_search_item
            })
            mock_response = self._get_mock_response(
                spider.domain,
                spider.parse_mbc_list,
                meta=meta
            )

            results = list(spider.parse_mbc_list(mock_response))
            requests = [x for x in results if not isinstance(x, AmazonProduct)]

            self.assertEqual(len(requests), 1)
            result = requests[0]
            self.assertEqual(result.callback, spider.parse_mbc_list)
            self.assertEqual(result.url, self._get_mock_mbc_list_next_page())

    def test_retains_meta_when_redirects_to_next_page(self):
        for spider_type in ['search', 'asins', 'category']:
            spider = self._get_spider(self._get_mock_scraper_mbc(), spider_type=spider_type)
            spider._collect = spider._collect_all
            meta = {
                'check_match': False,
                'parse_options': False,
                'test_value': 'value'
            }
            if spider.type == 'search':
                meta.update({
                'search_string': spider.current_search,
                'search_item': spider.current_search_item
            })
            mock_response = self._get_mock_response(
                spider.domain,
                spider.parse_mbc_list,
                meta=meta
            )

            results = list(spider.parse_mbc_list(mock_response))
            requests = [x for x in results if not isinstance(x, AmazonProduct)]

            self.assertEqual(len(requests), 1)
            result = requests[0]
            self.assertEqual(result.callback, spider.parse_mbc_list)
            self.assertEqual(result.url, self._get_mock_mbc_list_next_page())
            self.assertIn('test_value', result.meta.keys())
            self.assertEqual(result.meta['test_value'], 'value')

    def test_redirects_to_seller_details_if_no_seller_name(self):
        for spider_type in ['search', 'asins', 'category']:
            spider = self._get_spider(self._get_mock_scraper_mbc(next_page=False, products_no_vendor_name=True),
                                      spider_type=spider_type)
            spider._collect = spider._collect_all
            meta = {
                'check_match': False,
                'parse_options': False
            }
            if spider.type == 'search':
                meta.update({
                'search_string': spider.current_search,
                'search_item': spider.current_search_item
            })
            mock_response = self._get_mock_response(
                spider.domain,
                spider.parse_mbc_list,
                meta=meta
            )

            results = list(spider.parse_mbc_list(mock_response))

            expected_urls = [x['seller_url'] for x in self._get_mock_mbc_list_products_no_vendor_name()]
            self.assertEqual(len(results), len(expected_urls))
            for result in results:
                self.assertEqual(result.callback, spider.parse_vendor)
                self.assertIn(result.url, expected_urls)

    def test_redirects_to_reviews_if_enabled_and_no_next_page(self):
        for spider_type in ['search', 'asins', 'category']:
            spider = self._get_spider(self._get_mock_scraper_mbc(next_page=False), spider_type=spider_type)
            spider.collect_reviews = True
            spider.reviews_only_matched = False
            spider._collect = spider._collect_all
            meta = {
                'check_match': False,
                'parse_options': False,
                'found_item': {
                    'identifier': 'main_id',
                    'reviews_url': 'http://reviews1'
                }
            }
            if spider.type == 'search':
                meta.update({
                    'search_string': spider.current_search,
                    'search_item': spider.current_search_item
                })
            mock_response = self._get_mock_response(
                spider.domain,
                spider.parse_mbc_list,
                meta=meta
            )

            results = list(spider.parse_mbc_list(mock_response))
            requests = [x for x in results if not isinstance(x, AmazonProduct)]

            self.assertEqual(len(requests), 1)

            result = requests[0]

            self.assertEqual(result.url, 'http://reviews1')
            self.assertEqual(result.callback, spider.parse_reviews)

    def test_adds_seller_to_cache(self):
        for spider_type in ['search', 'asins', 'category']:
            spider = self._get_spider(self._get_mock_scraper_mbc(), spider_type=spider_type)
            spider._collect = spider._collect_all
            meta = {
                'check_match': False,
                'parse_options': False
            }
            if spider.type == 'search':
                meta.update({
                    'search_string': spider.current_search,
                    'search_item': spider.current_search_item
                })
            mock_response = self._get_mock_response(
                spider.domain,
                spider.parse_mbc_list,
                meta=meta
            )

            list(spider.parse_mbc_list(mock_response))

            expected_sellers = {x['seller_identifier']: x['vendor'] for x in self._get_mock_mbc_list_products()}

            self.assertEqual(len(expected_sellers), len(spider.sellers_cache))
            for seller_id, seller_name in spider.sellers_cache.items():
                self.assertIn(seller_id, expected_sellers)
                self.assertEqual(seller_name, expected_sellers[seller_id])

    def test_gets_seller_from_cache(self):
        for spider_type in ['search', 'asins']:
            spider = self._get_spider(self._get_mock_scraper_mbc(next_page=False, products_no_vendor_name=True),
                                      spider_type=spider_type)
            spider._collect = spider._collect_all
            meta = {
                'check_match': False,
                'parse_options': False
            }
            if spider.type == 'search':
                meta.update({
                    'search_string': spider.current_search,
                    'search_item': spider.current_search_item
                })
            mock_response = self._get_mock_response(
                spider.domain,
                spider.parse_mbc_list,
                meta=meta
            )

            seller_ids = [x['seller_identifier'] for x in self._get_mock_mbc_list_products_no_vendor_name()]
            cache = {}
            for seller_id in seller_ids:
                cache[seller_id] = 'AM - ' + seller_id

            spider.sellers_cache = cache

            list(spider.parse_mbc_list(mock_response))

            self.assertEqual(len(self._get_mock_mbc_list_products_no_vendor_name()), len(spider.collected_items))
            for product in spider.collected_items:
                seller_id = product['identifier'].split(':')[-1]
                self.assertEqual(product['dealer'], cache[seller_id])

    def test_gets_seller_from_cache_category_type(self):
        spider = self._get_spider(self._get_mock_scraper_mbc(next_page=False, products_no_vendor_name=True),
                                  spider_type="category")
        spider._collect = spider._collect_all
        meta = {
            'check_match': False,
            'parse_options': False
        }
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_mbc_list,
            meta=meta
        )

        seller_ids = [x['seller_identifier'] for x in self._get_mock_mbc_list_products_no_vendor_name()]
        cache = {}
        for seller_id in seller_ids:
            cache[seller_id] = 'AM - ' + seller_id

        spider.sellers_cache = cache

        results = list(spider.parse_mbc_list(mock_response))

        items = [x for x in results if isinstance(x, AmazonProduct)]

        self.assertEqual(len(self._get_mock_mbc_list_products_no_vendor_name()), len(items))
        for product in items:
            seller_id = product['identifier'].split(':')[-1]
            self.assertEqual(product['dealer'], cache[seller_id])

    def test_gets_seller_cache_from_file(self):
        import csv
        from tempfile import NamedTemporaryFile

        seller_ids = [x['seller_identifier'] for x in self._get_mock_mbc_list_products_no_vendor_name()]
        cache = {}
        for seller_id in seller_ids:
            cache[seller_id] = 'AM - ' + seller_id

        cache_file = NamedTemporaryFile('w+')
        f = cache_file.file
        writer = csv.DictWriter(f, ['identifier', 'dealer'])
        writer.writeheader()
        for seller_id, seller_name in cache.items():
            writer.writerow({
                'identifier': ':id:' + seller_id,
                'dealer': seller_name
            })
        f.flush()

        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            cache_filename = cache_file.name

            def _collect_best_match(self, item, search_string):
                self.collected_items.append(item)

        spider = TestSpider('amazon.com')
        f.close()
        spider.scraper = self._get_mock_scraper_mbc(next_page=False, products_no_vendor_name=True)
        spider.collected_items = []
        spider.current_search_item = {'name': 'item', 'price': '1.5'}
        spider.current_search = 'item'

        spider._collect = spider._collect_all
        mock_response = self._get_mock_response(
            spider.domain,
            spider.parse_mbc_list,
            meta={
                'search_string': spider.current_search,
                'search_item': spider.current_search_item,
                'check_match': False,
                'parse_options': False
            }
        )

        list(spider.parse_mbc_list(mock_response))

        self.assertEqual(len(self._get_mock_mbc_list_products_no_vendor_name()), len(spider.collected_items))
        for product in spider.collected_items:
            seller_id = product['identifier'].split(':')[-1]
            self.assertEqual(product['dealer'], cache[seller_id])

    def test_not_redirects_to_product_details_if_seller_in_cache(self):
        for spider_type in ['search', 'asins', 'category']:
            spider = self._get_spider(self._get_mock_scraper_mbc(next_page=False, products_no_vendor_name=True),
                                      spider_type=spider_type)
            spider._collect = spider._collect_all
            meta = {
                'check_match': False,
                'parse_options': False
            }
            if spider.type == 'search':
                meta.update({
                    'search_string': spider.current_search,
                    'search_item': spider.current_search_item
                })
            mock_response = self._get_mock_response(
                spider.domain,
                spider.parse_mbc_list,
                meta=meta
            )

            seller_ids = [x['seller_identifier'] for x in self._get_mock_mbc_list_products_no_vendor_name()]
            cache = {}
            for seller_id in seller_ids:
                cache[seller_id] = 'AM - ' + seller_id

            spider.sellers_cache = cache

            results = list(spider.parse_mbc_list(mock_response))
            requests = [x for x in results if not isinstance(x, AmazonProduct)]

            self.assertEqual(len(requests), 0)
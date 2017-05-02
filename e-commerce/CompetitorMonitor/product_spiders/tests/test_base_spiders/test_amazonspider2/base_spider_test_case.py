# -*- coding: utf-8 -*-
from copy import deepcopy
import datetime
import unittest

from scrapy.http import Request, HtmlResponse


class AmazonBaseTestCase(unittest.TestCase):
    def _get_mock_items(self):
        return [
            {
                'name': 'item1',
                'price': '1.0',
                'identifier': 'item1',
                'url': 'http://url1',
                'reviews_url': 'http://reviews1',
                'mbc_list_url_new': 'http://mbc_new1',
                'mbc_list_url_used': 'http://mbc_used1'
            },
            {
                'name': 'item2',
                'price': '2.0',
                'identifier': 'item2',
                'url': 'http://url2',
                'reviews_url': 'http://reviews2',
                'mbc_list_url_new': 'http://mbc_new1',
                'mbc_list_url_used': 'http://mbc_used1'
            }
        ]

    def _get_mock_suggested_search_urls(self):
        return [
            'http://amazon.com/s/suggested'
        ]

    def _get_mock_next_page_url(self):
        return 'http://amazon.com/s/next'

    def _get_mock_item(self, vendor=True):
        return {
            'name': 'item1',
            'name_with_options': '',
            'price': '1.0',
            'identifier': 'item1',
            'brand': '',
            'image_url': '',
            'url': 'http://url1',
            'reviews_url': 'http://reviews_url1',
            'shipping_cost': '',
            'model': '',
            'vendor': 'ASD' if vendor else '',
            'used_vendor': '',
            'option_texts': [],
            'options': [
                {
                    'texts': 'option1',
                    'url': 'http://option1',
                    'identifier': 'option1'
                },
                {
                    'texts': 'option2',
                    'url': 'http://option2',
                    'identifier': 'option2'
                }
            ],
            'mbc_list_url_new': 'http://mbc_new1',
            'mbc_list_url_used': 'http://mbc_used1',
            'asin': 'item1',
            'ajax_price_url': None,
            'unavailable': False
        }

    def _get_mock_reviews(self):
        return [
            {
                'date': datetime.datetime.now(),
                'rating': 5,
                'url': 'http://review_url1',
                'identifier': 'review1',
                'full_text': u'%s\n%s' % ("Review", "Text")
            },
            {
                'date': datetime.datetime.now(),
                'rating': 4,
                'url': 'http://review_url2',
                'identifier': 'review2',
                'full_text': u'%s\n%s' % ("Review", "Text")
            }
        ]

    def _get_mock_reviews2(self):
        return [
            {
                'date': datetime.datetime.now(),
                'rating': 3,
                'url': 'http://review_url3',
                'identifier': 'review3',
                'full_text': u'%s\n%s' % ("Review", "Text")
            }
        ]

    def _get_mock_reviews_next_page(self):
        return 'http://next_reviews1'

    def _get_mock_mbc_list_products(self):
        return [
            {
                "seller_identifier": "seller1",
                "name": "item1",
                "url": "http://item1",
                "price": "10.00",
                "vendor": "AM - seller1",
                "image_url": "http://image1",
                "identifier": "id1",
                "brand": "brand1",
                "seller_url": "http://seller1"
            },
            {
                "seller_identifier": "seller2",
                "name": "item1",
                "url": "http://item2",
                "price": "11.00",
                "vendor": "AM - seller2",
                "image_url": "http://image1",
                "identifier": "id1",
                "brand": "brand1",
                "seller_url": "http://seller2"
            },
        ]

    def _get_mock_mbc_list_products_no_vendor_name(self):
        return [
            {
                "seller_identifier": "seller1",
                "name": "item1",
                "url": "http://item1",
                "price": "10.00",
                "vendor": "",
                "image_url": "http://image1",
                "identifier": "id1",
                "brand": "brand1",
                "seller_url": "http://seller1"
            },
            {
                "seller_identifier": "seller2",
                "name": "item1",
                "url": "http://item2",
                "price": "11.00",
                "vendor": "",
                "image_url": "http://image1",
                "identifier": "id1",
                "brand": "brand1",
                "seller_url": "http://seller2"
            },
        ]

    def _get_mock_mbc_list_products_one_with_vendor_one_without(self):
        return [
            {
                "seller_identifier": "seller1",
                "name": "item1",
                "url": "http://item1",
                "price": "10.00",
                "vendor": "AM - seller1",
                "image_url": "http://image1",
                "identifier": "id1",
                "brand": "brand1"
            },
            {
                "seller_identifier": "seller2",
                "name": "item1",
                "url": "http://item2",
                "price": "11.00",
                "vendor": "",
                "image_url": "http://image1",
                "identifier": "id1",
                "brand": "brand1"
            },
        ]

    def _get_mock_mbc_list_next_page(self):
        return 'http://next_mbc_list1'

    def _get_mock_scraper_products_list(
            self,
            products=True,
            suggestions=False,
            suggested_urls=False,
            next_url=False,
            results_count=None,
            is_non_specific_cat_results=None
    ):
        mock_scraper = MockScraper()
        if products:
            mock_items = self._get_mock_items()
            if suggestions:
                mock_items, mock_items2 = [[x] for x in mock_items]
                mock_scraper.set_search_results_products(mock_items)
                mock_scraper.set_search_results_suggested_products(mock_items2)
            else:
                mock_scraper.set_search_results_products(mock_items)
        else:
            mock_items = self._get_mock_items()
            if suggestions:
                mock_scraper.set_search_results_suggested_products(mock_items)
        if suggested_urls:
            mock_scraper.set_search_results_suggested_search_urls(self._get_mock_suggested_search_urls())
        if next_url:
            mock_scraper.set_search_results_next_url(self._get_mock_next_page_url())
        if results_count:
            mock_scraper.set_search_results_count(results_count)
        if is_non_specific_cat_results is not None:
            mock_scraper.set_is_non_specific_cat_results(is_non_specific_cat_results)
        return mock_scraper

    def _get_mock_scraper_products_list_products_and_suggestions(self):
        return self._get_mock_scraper_products_list(products=True, suggestions=True)

    def _get_mock_scraper_products_list_suggestions(self):
        return self._get_mock_scraper_products_list(products=False, suggestions=True)

    def _get_mock_scraper_product_details(self, vendor=True, price=True, ajax_price_url=False):
        mock_item = self._get_mock_item(vendor)
        if not price:
            mock_item['price'] = None
        if ajax_price_url:
            mock_item['ajax_price_url'] = 'http://ajax_price_url'
        mock_scraper = MockScraper()
        mock_scraper.set_product_details(mock_item)
        return mock_scraper

    def _get_mock_scraper_reviews(
            self,
            reviews=False,
            next_page=False
    ):
        mock_scraper = MockScraper()
        if reviews:
            mock_scraper.set_reviews(self._get_mock_reviews())
        if next_page:
            mock_scraper.set_reviews_next_url(self._get_mock_reviews_next_page())

        return mock_scraper

    def _get_mock_scraper_mbc(self, products=True, next_page=True, products_no_vendor_name=False):
        mock_scraper = MockScraper()
        if products:
            if products_no_vendor_name:
                mock_scraper.set_mbc_list_products(self._get_mock_mbc_list_products_no_vendor_name())
            else:
                mock_scraper.set_mbc_list_products(self._get_mock_mbc_list_products())
        if next_page:
            mock_scraper.set_mbc_list_next_url(self._get_mock_mbc_list_next_page())

        return mock_scraper

    def _get_spider(self, mock_scraper):
        raise NotImplementedError("Please implement `_get_spider` function to test")

    def _get_mock_response(self, domain, callback, meta, body=''):
        url = 'http://%s/s/something' % domain
        mock_request = Request(url, callback=callback, meta=meta)
        mock_response = HtmlResponse(url, request=mock_request, body=body)
        return mock_response

    def _get_mock_response_reviews(self, domain, callback, meta, body=''):
        url = 'http://%s/s/something' % domain
        # Fix for part of code checking of reviews sorting order
        url += "?sortBy=bySubmissionDateDescending"
        mock_request = Request(url, callback=callback, meta=meta)
        mock_response = HtmlResponse(url, request=mock_request, body=body)
        return mock_response

    def _make_response_out_of_request(self, request):
        mock_response = HtmlResponse(request.url, request=request)
        return mock_response

    def _make_response_out_of_request_reviews(self, request):
        url = request.url
        url += "?sortBy=bySubmissionDateDescending"
        mock_response = HtmlResponse(url, request=request)
        return mock_response


class MockCrawler(object):
    """
    Mock crawler for testing purposes
    """
    def __init__(self, engine):
        self.engine = engine


class MockEngine(object):
    """
    Mock engine for testing purposes. Together with MockCrawler used when testing methods, where spider can't
    directly yield requests but instead has to use crawler.engine._crawl (mainly spider_idle methods)
    """
    def __init__(self):
        self.last_request = None
        self.last_spider = None

        self.crawl_called = 0

    def crawl(self, request, spider):
        self.last_request = request
        self.last_spider = spider

        self.crawl_called += 1


class MockScraper(object):
    """
    Mock scraper used when testing spider general collecting work
    """
    def __init__(self):
        self.search_results = {
            'products': [],
            'suggested_products': [],
            'suggested_search_urls': [],
            'next_url': None,
            'current_page': None,
            'results_count': None,
            'is_non_specific_cat_results': False
        }
        self.scrape_search_results_page_called = 0
        self.antibot_protection_raised_called = 0

        self.product_details_results = {
            'name': '',
            'name_with_options': '',
            'brand': '',
            'price': '',
            'identifier': '',
            'url': '',
            'image_url': '',
            'shipping_cost': '',
            'model': '',
            'vendor': '',
            'used_vendor': '',
            'option_texts': [],
            'options': [],
            'reviews_url': ''
        }
        self.scrape_product_details_called = 0

        self.reviews_results = {
            'next_url': '',
            'current_page': 1,
            'reviews': ''
        }
        self.scrape_reviews_list_page_called = 0

        self.mbc_list_results = {
            'next_url': '',
            'current_page': 1,
            'products': []
        }
        self.scrape_mbc_list_called = 0

    def set_search_results_products(self, products):
        self.search_results['products'] = products

    def set_search_results_suggested_products(self, suggested_products):
        self.search_results['suggested_products'] = suggested_products

    def set_search_results_suggested_search_urls(self, suggested_search_urls):
        self.search_results['suggested_search_urls'] = suggested_search_urls

    def set_search_results_next_url(self, next_url):
        self.search_results['next_url'] = next_url

    def set_search_results_current_page(self, current_page):
        self.search_results['current_page'] = current_page

    def set_search_results_count(self, results_count):
        self.search_results['results_count'] = results_count

    def set_is_non_specific_cat_results(self, is_non_specific_cat_results):
        self.search_results['is_non_specific_cat_results'] = is_non_specific_cat_results

    def set_product_details(self, item):
        self.product_details_results = deepcopy(item)

    def set_reviews(self, reviews):
        self.reviews_results['reviews'] = reviews

    def set_reviews_next_url(self, next_url):
        self.reviews_results['next_url'] = next_url

    def set_mbc_list_products(self, products):
        self.mbc_list_results['products'] = products

    def set_mbc_list_next_url(self, next_url):
        self.mbc_list_results['next_url'] = next_url

    def antibot_protection_raised(self, text):
        self.antibot_protection_raised_called += 1
        return False

    def scrape_search_results_page(self, response, amazon_direct=False):
        self.scrape_search_results_page_called += 1
        return self.search_results

    def scrape_product_details_page(self, response, only_color=False,
                                    collect_new_products=True,
                                    collect_used_products=False):
        self.scrape_product_details_called += 1
        return self.product_details_results

    def scrape_reviews_list_page(self, response, inc_selector=False, collect_author=False, collect_author_url=False):
        self.scrape_reviews_list_page_called += 1
        return self.reviews_results

    def scrape_mbc_list_page(self, response):
        self.scrape_mbc_list_called += 1
        return self.mbc_list_results
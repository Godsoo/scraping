# -*- coding: utf-8 -*-
from unittest import TestCase

from productspidersweb.spider_ratings import _calculate_rating


class TestRatingCalculation(TestCase):
    def test_empty(self):
        self.assertEqual(_calculate_rating({}), 0)

    def test_simple_feed(self):
        params = {
            'blocking': False,
            'crawl_method': {'value': 'feed'},
            'many_products': False,
            'parse_prev_results': False}
        self.assertEqual(_calculate_rating(params), 1)

    def test_simple_amazon(self):
        params = {
            'blocking': False,
            'crawl_method': {
                'subvalues': {
                    'custom_crawling': False,
                    'custom_scraping': False},
                'value': 'amazon'},
            'many_products': False,
            'parse_prev_results': False}
        self.assertEqual(_calculate_rating(params), 2)

    def test_amazon_options(self):
        params = {
            'blocking': False,
            'crawl_method': {
                'subvalues': {
                    'custom_crawling': False,
                    'custom_scraping': True},
                'value': 'amazon'},
            'many_products': False,
            'parse_prev_results': False}
        self.assertEqual(_calculate_rating(params), 4)

    def test_simple_ebay(self):
        params = {
            'blocking': False,
            'crawl_method': {
                'subvalues': {
                    'custom_crawling': False,
                    'custom_scraping': False},
                'value': 'ebay'},
            'many_products': False,
            'parse_prev_results': False}
        self.assertEqual(_calculate_rating(params), 2)

    def test_ebay_options(self):
        params = {
            'blocking': False,
            'crawl_method': {
                'subvalues': {
                    'custom_crawling': False,
                    'custom_scraping': True},
                'value': 'ebay'},
            'many_products': False,
            'parse_prev_results': False}
        self.assertEqual(_calculate_rating(params), 4)

    def test_formula_case(self):
        params = {
            'blocking': False,
            'crawl_method': {
                'subvalues': {
                    'add_meta': None,
                    'ajax': False,
                    'asp_net': False,
                    'bad_html': False,
                    'cookies': False,
                    'currency': False,
                    'from_feed': False,
                    'mixins': {
                        'bsm': False, 'primary': False, 'productcache': False},
                    'options': False,
                    'phantom_js': True,
                    'price_transform': False,
                    'quirks': {
                        'quirk_crawling': False, 'quirk_field': None},
                    'reviews': True,
                    'sellers': True,
                    'stock': False,
                    'type': {
                        'value': 'full_site'}},
                'value': 'regular'},
            'many_products': False,
            'parse_prev_results': False}
        self.assertEqual(_calculate_rating(params), 8)

        params['crawl_method']['subvalues']['bad_html'] = True

        self.assertEqual(_calculate_rating(params), 16)

    def test_formula_case_2(self):
        params = {
            'blocking': False,
            'crawl_method': {
                'subvalues': {
                    'add_meta': None,
                    'ajax': True,
                    'asp_net': False,
                    'bad_html': False,
                    'cookies': False,
                    'currency': False,
                    'from_feed': False,
                    'mixins': {
                        'bsm': False, 'primary': False, 'productcache': False},
                    'options': False,
                    'phantom_js': True,
                    'price_transform': False,
                    'quirks': {
                        'quirk_crawling': False, 'quirk_field': None},
                    'reviews': True,
                    'sellers': True,
                    'stock': False,
                    'type': {
                        'value': 'full_site'}},
                'value': 'regular'},
            'many_products': False,
            'parse_prev_results': False}

        self.assertEqual(_calculate_rating(params), 9)

        params['crawl_method']['subvalues']['asp_net'] = True

        self.assertEqual(_calculate_rating(params), 10)
    def test_complex_case(self):
        params = {
            'blocking': False,
            'crawl_method': {
                'subvalues': {
                    'add_meta': ['asd', 'qwe'],
                    'ajax': False,
                    'asp_net': False,
                    'bad_html': False,
                    'cookies': False,
                    'currency': True,
                    'from_feed': False,
                    'mixins': {'bsm': False, 'primary': False, 'productcache': False},
                    'options': True,
                    'phantom_js': False,
                    'price_transform': False,
                    'quirks': {
                        'quirk_crawling': True, 'quirk_field': None},
                    'reviews': False,
                    'sellers': False,
                    'stock': False,
                    'type': {
                        'value': 'search'}},
                'value': 'regular'},
            'many_products': False,
            'parse_prev_results': False}
        self.assertEqual(_calculate_rating(params), 9)

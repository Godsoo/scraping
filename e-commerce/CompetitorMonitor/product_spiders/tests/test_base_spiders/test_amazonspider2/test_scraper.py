# -*- coding: utf-8 -*-
import datetime
from decimal import Decimal
import json
import os.path
import unittest
import os.path

from product_spiders.base_spiders.amazonspider2 import AmazonScraper
from product_spiders.response_utils import retrieve_response, download_response

here = os.path.abspath(os.path.dirname(__file__))
fixtures_path = os.path.join(here, 'fixtures')


class TestAmazonScraper(unittest.TestCase):
    """
    Tests all scraper functions
    """
    def test_scrapes_search_results(self):
        response = retrieve_response(os.path.join(fixtures_path, 'search1'))
        self.assertIsNotNone(response)
        results_file = os.path.join(fixtures_path, 'search1_results/results.json')

        scraper = AmazonScraper()

        result = scraper.scrape_search_results_page(response)
        expected = json.load(open(results_file))

        # test next page url, current page number
        if expected['next_url'] is None:
            self.assertIsNone(result['next_url'])
        else:
            self.assertEqual(result['next_url'], expected['next_url'])
        if expected['current_page'] is None:
            self.assertIsNone(result['current_page'])
        else:
            self.assertEqual(result['current_page'], expected['current_page'])

        if expected['results_count'] is None:
            self.assertIsNone(result['results_count'])
        else:
            self.assertEqual(result['results_count'], expected['results_count'])

        # check links to suggested searches
        for link in expected['suggested_search_urls']:
            self.assertIn(link, result['suggested_search_urls'])

        # check number of products and suggested products matches
        self.assertEqual(len(expected['products']), len(result['products']))
        self.assertEqual(len(expected['suggested_products']), len(result['suggested_products']))

        for product in expected['suggested_products']:
            found_products = [x for x in result['suggested_products'] if x['identifier'] == product['identifier']]
            self.assertGreater(len(found_products), 0, "Not found product with identifier: %s" % product['identifier'])
            self.assertLess(len(found_products), 2, "Found more than 1 product with identifier: %s" % product['identifier'])
            found_product = found_products.pop()

            for key, value in product.items():
                if key == 'price':
                    self.assertEqual(found_product[key], Decimal(value),
                                     "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))
                else:
                    self.assertEqual(found_product[key], value,
                                     "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))

        for product in expected['products']:
            found_products = [x for x in result['products'] if x['identifier'] == product['identifier']]
            self.assertGreater(len(found_products), 0, "Not found product with identifier: %s" % product['identifier'])
            self.assertLess(len(found_products), 2, "Found more than 1 product with identifier: %s" % product['identifier'])
            found_product = found_products.pop()

            for key, value in product.items():
                if key == 'price':
                    if isinstance(value, list):
                        value = tuple([Decimal(x) for x in value])
                    else:
                        value = Decimal(value)
                    self.assertEqual(found_product[key], value,
                                     "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))
                else:
                    self.assertEqual(found_product[key], value,
                                     "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))

    def test_scrapes_search_results2(self):
        response = retrieve_response(os.path.join(fixtures_path, 'search2'))
        self.assertIsNotNone(response)
        results_file = os.path.join(fixtures_path, 'search2_results/results.json')

        scraper = AmazonScraper()

        result = scraper.scrape_search_results_page(response)
        expected = json.load(open(results_file))

        # test next page url, current page number
        if expected['next_url'] is None:
            self.assertIsNone(result['next_url'])
        else:
            self.assertEqual(result['next_url'], expected['next_url'])
        if expected['current_page'] is None:
            self.assertIsNone(result['current_page'])
        else:
            self.assertEqual(result['current_page'], expected['current_page'])

        if expected['results_count'] is None:
            self.assertIsNone(result['results_count'])
        else:
            self.assertEqual(result['results_count'], expected['results_count'])

        # check links to suggested searches
        for link in expected['suggested_search_urls']:
            self.assertIn(link, result['suggested_search_urls'])

        # check number of products and suggested products matches
        self.assertEqual(len(expected['products']), len(result['products']))
        self.assertEqual(len(expected['suggested_products']), len(result['suggested_products']))

        for product in expected['suggested_products']:
            found_products = [x for x in result['suggested_products'] if x['identifier'] == product['identifier']]
            self.assertGreater(len(found_products), 0, "Not found product with identifier: %s" % product['identifier'])
            self.assertLess(len(found_products), 2, "Found more than 1 product with identifier: %s" % product['identifier'])
            found_product = found_products.pop()

            for key, value in product.items():
                if key == 'price':
                    self.assertEqual(found_product[key], Decimal(value),
                                     "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))
                else:
                    self.assertEqual(found_product[key], value,
                                     "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))

        for product in expected['products']:
            found_products = [x for x in result['products'] if x['identifier'] == product['identifier']]
            self.assertGreater(len(found_products), 0, "Not found product with identifier: %s" % product['identifier'])
            self.assertLess(len(found_products), 2, "Found more than 1 product with identifier: %s" % product['identifier'])
            found_product = found_products.pop()

            for key, value in product.items():
                if key == 'price':
                    self.assertEqual(found_product[key], Decimal(value),
                                     "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))
                else:
                    self.assertEqual(found_product[key], value,
                                     "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))

    def test_scrapes_mbc_list(self):
        response = retrieve_response(os.path.join(fixtures_path, 'mbc_list'))
        self.assertIsNotNone(response)
        results_file = os.path.join(fixtures_path, 'mbc_list_results/results.json')

        scraper = AmazonScraper()

        result = scraper.scrape_mbc_list_page(response)

        expected = json.load(open(results_file))

        # test next page url, current page number
        if expected['next_url'] is None:
            self.assertIsNone(result['next_url'])
        else:
            self.assertEqual(result['next_url'], expected['next_url'])
        if expected['current_page'] is None:
            self.assertIsNone(result['current_page'])
        else:
            self.assertEqual(result['current_page'], expected['current_page'])

        # check number of products and suggested products matches
        self.assertEqual(len(expected['products']), len(result['products']))

        for product in expected['products']:
            found_products = [x for x in result['products'] if
                              x['identifier'] == product['identifier'] and
                              x['seller_identifier'] == product['seller_identifier']]
            self.assertGreater(len(found_products), 0, "Not found product with identifier: %s" % product['identifier'])
            self.assertLess(len(found_products), 2, "Found more than 1 product with identifier: %s" % product['identifier'])
            found_product = found_products.pop()

            for key, value in product.items():
                if key == 'price':
                    self.assertEqual(found_product[key], Decimal(value),
                                     "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))
                else:
                    self.assertEqual(found_product[key], value,
                                     "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))

    def test_scrapes_reviews(self):
        response = retrieve_response(os.path.join(fixtures_path, 'reviews_list'))
        self.assertIsNotNone(response)
        results_file = os.path.join(fixtures_path, 'reviews_list_results/results.json')

        scraper = AmazonScraper()

        result = scraper.scrape_reviews_list_page(response)

        expected = json.load(open(results_file))

        for review in expected['reviews']:
            review['date'] = datetime.datetime.strptime(review['date'], "%Y-%m-%dT%H:%M:%S")

        # test next page url, current page number
        if expected['next_url'] is None:
            self.assertIsNone(result['next_url'])
        else:
            self.assertEqual(result['next_url'], expected['next_url'])
        if expected['current_page'] is None:
            self.assertIsNone(result['current_page'])
        else:
            self.assertEqual(result['current_page'], expected['current_page'])

        # check number of products and suggested products matches
        self.assertEqual(len(expected['reviews']), len(result['reviews']))

        for review in expected['reviews']:
            found_products = [x for x in result['reviews'] if
                              x['identifier'] == review['identifier']]
            self.assertGreater(len(found_products), 0, "Not found product with identifier: %s" % review['identifier'])
            self.assertLess(len(found_products), 2, "Found more than 1 product with identifier: %s" % review['identifier'])
            found_product = found_products.pop()

            for key, value in review.items():
                if key == 'price':
                    self.assertEqual(found_product[key], Decimal(value),
                                     "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))
                else:
                    self.assertEqual(found_product[key], value,
                                     "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))

    def test_scrapes_product_details(self):
        response = retrieve_response(os.path.join(fixtures_path, 'product'))
        self.assertIsNotNone(response)
        results_file = os.path.join(fixtures_path, 'product_results/results.json')

        scraper = AmazonScraper()

        result = scraper.scrape_product_details_page(response)

        expected = json.load(open(results_file))

        for key, value in expected.items():
            if not isinstance(value, list):
                self.assertIn(key, result.keys())
                if value is None:
                    self.assertIsNone(result[key])
                else:
                    if key == 'price':
                        if '-' in value:
                            low, high = value.split("-")
                            low = Decimal(low)
                            high = Decimal(high)
                            self.assertEqual(result[key], (low, high),
                                             "Field %s does not match: expected '%s', found '%s'" % (key, value, result[key]))
                        else:
                            self.assertEqual(result[key], Decimal(value),
                                             "Field %s does not match: expected '%s', found '%s'" % (key, value, result[key]))
                    else:
                        self.assertEqual(result[key], value,
                                         "Field %s does not match: expected '%s', found '%s'" % (key, value, result[key]))

        self.assertEqual(len(expected['option_texts']), len(result['option_texts']))

        for option_text in expected['option_texts']:
            self.assertIn(option_text, result['option_texts'])

        self.assertEqual(len(expected['options']), len(result['options']))

        for option in expected['options']:
            found_options = [x for x in result['options'] if
                              x['identifier'] == option['identifier']]
            self.assertGreater(len(found_options), 0, "Not found option with identifier: %s" % option['identifier'])
            self.assertLess(len(found_options), 2, "Found more than 1 option with identifier: %s" % option['identifier'])
            found_product = found_options.pop()

            for key, value in option.items():
                if key == 'price':
                    if '-' in value:
                        low, high = value.split("-")
                        low = Decimal(low)
                        high = Decimal(high)
                        self.assertEqual(found_product[key], (low, high),
                                         "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))
                    else:
                        self.assertEqual(found_product[key], Decimal(value),
                                         "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))
                else:
                    self.assertEqual(found_product[key], value,
                                     "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))

    def test_scrapes_product_details_option_size_colour(self):
        response = retrieve_response(os.path.join(fixtures_path, 'product_option_size_colour'))
        self.assertIsNotNone(response)
        results_file = os.path.join(fixtures_path, 'product_option_size_colour_results/results.json')

        scraper = AmazonScraper()

        result = scraper.scrape_product_details_page(response)

        expected = json.load(open(results_file))

        self.assertEqual(len(expected['option_texts']), len(result['option_texts']))

        for key, value in expected.items():
            if not isinstance(value, list):
                if value is None:
                    self.assertIsNone(result[key])
                else:
                    if key == 'price':
                        self.assertEqual(result[key], Decimal(value),
                                         "Field %s does not match: expected '%s', found '%s'" % (key, value, result[key]))
                    else:
                        self.assertEqual(result[key], value,
                                         "Field %s does not match: expected '%s', found '%s'" % (key, value, result[key]))

        for option_text in expected['option_texts']:
            self.assertIn(option_text, result['option_texts'])

        self.assertEqual(len(expected['options']), len(result['options']))

        for option in expected['options']:
            found_options = [x for x in result['options'] if
                              x['identifier'] == option['identifier']]
            self.assertGreater(len(found_options), 0, "Not found option with identifier: %s" % option['identifier'])
            self.assertLess(len(found_options), 2, "Found more than 1 option with identifier: %s" % option['identifier'])
            found_product = found_options.pop()

            for key, value in option.items():
                if key == 'price':
                    self.assertEqual(found_product[key], Decimal(value),
                                     "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))
                else:
                    self.assertEqual(found_product[key], value,
                                     "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))

    def test_scrapes_product_details_option_colour(self):
        response = retrieve_response(os.path.join(fixtures_path, 'product_option_colour'))
        self.assertIsNotNone(response)
        results_file = os.path.join(fixtures_path, 'product_option_colour_results/results.json')

        scraper = AmazonScraper()

        result = scraper.scrape_product_details_page(response)

        expected = json.load(open(results_file))

        self.assertEqual(len(expected['option_texts']), len(result['option_texts']))

        for key, value in expected.items():
            if not isinstance(value, list):
                if value is None:
                    self.assertIsNone(result[key])
                else:
                    if key == 'price':
                        self.assertEqual(result[key], Decimal(value),
                                         "Field %s does not match: expected '%s', found '%s'" % (key, value, result[key]))
                    else:
                        self.assertEqual(result[key], value,
                                         "Field %s does not match: expected '%s', found '%s'" % (key, value, result[key]))

        for option_text in expected['option_texts']:
            self.assertIn(option_text, result['option_texts'])

        self.assertEqual(len(expected['options']), len(result['options']))

        for option in expected['options']:
            found_options = [x for x in result['options'] if
                              x['identifier'] == option['identifier']]
            self.assertGreater(len(found_options), 0, "Not found option with identifier: %s" % option['identifier'])
            self.assertLess(len(found_options), 2, "Found more than 1 option with identifier: %s" % option['identifier'])
            found_product = found_options.pop()

            for key, value in option.items():
                if key == 'price':
                    self.assertEqual(found_product[key], Decimal(value),
                                     "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))
                else:
                    self.assertEqual(found_product[key], value,
                                     "Field %s does not match: expected '%s', found '%s'" % (key, value, found_product[key]))

    def test_empties_mbc_urls_for_kindle_books(self):
        scraper = AmazonScraper()

        response = retrieve_response(os.path.join(fixtures_path, 'non_kindle_book'))
        self.assertIsNotNone(response)
        res = scraper.scrape_product_details_page(response)
        self.assertFalse(scraper.is_kindle_book(response))
        self.assertTrue(len(res['mbc_list_url_new']) > 0)
        self.assertTrue(len(res['mbc_list_url_used']) > 0)

        response = retrieve_response(os.path.join(fixtures_path, 'kindle_book'))
        self.assertIsNotNone(response)
        self.assertTrue(scraper.is_kindle_book(response))
        res = scraper.scrape_product_details_page(response)
        self.assertIsNone(res['mbc_list_url_new'])
        self.assertIsNone(res['mbc_list_url_used'])

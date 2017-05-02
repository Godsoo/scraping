# -*- coding: utf-8 -*-
import unittest
import random
from datetime import datetime, timedelta, date

import mock

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider, _filter_brand, _filter_name


class TestAmazonSpiderGeneral(unittest.TestCase):
    def test_adds_error_when_no_type_selected(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'

        spider = TestSpider()

        self.assertEqual(len(spider.errors), 1)
        self.assertIn('should be one of', spider.errors[0].lower())

    def test_spider_opened_loads_prev_reviews_if_enabled(self):
        # generate random reviews
        identifiers = ['id1', 'id2', 'id3']
        prev_crawl_meta = []
        newest_dates = {}

        for identifier in identifiers:
            res = {
                'identifier': identifier,
                'metadata': {
                    'reviews': []
                }
            }

            reviews_count = random.randint(1, 5)

            newest_date = None

            for i in xrange(0, reviews_count):
                rand_date = (datetime.now() - timedelta(days=random.randint(1, 10))).date()
                if newest_date is None or rand_date > newest_date:
                    newest_date = rand_date
                rand_date = rand_date.strftime(BaseAmazonSpider.review_date_format)
                res['metadata']['reviews'].append({
                    'date': rand_date
                })

            newest_dates[identifier] = newest_date
            prev_crawl_meta.append(res)

        # save reviews to file
        import json
        from tempfile import NamedTemporaryFile

        meta_file = NamedTemporaryFile('w+')
        f = meta_file.file
        json.dump(prev_crawl_meta, f)
        f.flush()

        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            domain = "amazon.com"
            type = "category"

            collect_reviews = True
            reviews_only_new = True

        spider = TestSpider()

        spider._amazon_get_prev_crawl_meta_file = mock.MagicMock(return_value=meta_file.name)

        spider._hack_fix_related_to_bug_18_02_to_14_03 = False

        spider.spider_opened(spider)

        f.close()

        for identifier, expected_newest_date in newest_dates.items():
            self.assertIn(identifier, spider.prev_crawl_reviews)

            found_newest_date = spider.prev_crawl_reviews[identifier]

            self.assertEqual(expected_newest_date, found_newest_date)

    def test_get_prev_crawl_meta_file(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            domain = "amazon.com"
            type = "category"

        spider = TestSpider()
        spider.prev_crawl_id = 11

        # None because file does not exists
        self.assertIsNone(spider._amazon_get_prev_crawl_meta_file())

        self.assertEqual(spider._amazon_get_prev_crawl_meta_filename(type='json'), 'data/meta/11_meta.json')

    def test_get_prev_crawl_meta_file_no_prev_crawl(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            domain = "amazon.com"
            type = "category"

        spider = TestSpider()

        self.assertIsNone(spider._amazon_get_prev_crawl_meta_file())

    def test_filter_brand(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            domain = "amazon.com"
            type = "category"

        expected_brands = [
            ('a' * 100, 'a' * 100),
            ('a' * 101, 'a' * 97 + '...'),
            ('asd', 'asd'),
            ('b' * 500, 'b' * 97 + '...')
        ]

        for brand, expected_res in expected_brands:
            res = _filter_brand(brand)
            self.assertLessEqual(len(res), 100)

            self.assertEqual(expected_res, res)

    def test_filter_name(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            domain = "amazon.com"
            type = "category"

        expected_names = [
            ('asd', 'asd'),
            ('qwe', 'qwe'),
            ('asd qwe aksdjah lkdha sl', 'asd qwe aksdjah lkdha sl'),
            ('new offers for 123', '123'),
        ]

        for name, expected_res in expected_names:
            res = _filter_name(name)

            self.assertEqual(expected_res, res)

    def test_match_price(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            domain = "amazon.com"
            type = "category"

        spider = TestSpider()

        # each tuple has format: (search_item price, new_item price, price_diff, expected output)
        expected_prices = [
            ('100.00', '55.00', 0.5, True),
            ('100.00', '50.00', 0.5, True),
            ('100.00', '49.99', 0.5, False),
            ('100.00', '50.00', 0.4, False),

            ('100.00', '155.00', 0.5, False),
            ('100.00', '150.00', 0.5, True),
            ('100.00', '150.01', 0.5, False),
            ('100.00', '149.99', 0.5, True),
            ('100.00', '150.00', 0.4, False),
        ]

        for search_item_price, new_item_price, price_diff, expected_res in expected_prices:
            search_item = {'price': search_item_price}
            new_item = {'price': new_item_price}
            res = spider.match_price(search_item, new_item, price_diff)

            self.assertEqual(expected_res, res)

    def test_match_name(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            domain = "amazon.com"
            type = "category"

        spider = TestSpider()

        # each tuple has format: (search_item name, new_item name, match_threshold, expected output)
        expected_names = [
            ('asd', 'asd', 90, True),
            ('asd', 'qwe', 90, False),
            ('asd qwe', 'asd', 90, True),
            ('asd qwe', 'asd zxc', 90, False)
        ]

        for search_item_name, new_item_name, price_diff, expected_res in expected_names:
            search_item = {'name': search_item_name}
            new_item = {'name': new_item_name}
            res = spider.match_name(search_item, new_item, price_diff)

            self.assertEqual(expected_res, res)

    def test_match_text(self):
        class TestSpider(BaseAmazonSpider):
            name = "Test Spider"
            domain = "amazon.com"
            type = "category"

        spider = TestSpider()

        # each tuple has format: (search_item name, text, match_threshold, expected output)
        expected_names = [
            ('asd', 'asd', 90, True),
            ('asd', 'qwe', 90, False),
            ('asd qwe', 'asd', 90, True),
            ('asd qwe', 'asd zxc', 90, False)
        ]

        for search_item_name, text, price_diff, expected_res in expected_names:
            search_item = {'name': search_item_name}
            res = spider.match_text(text, search_item, price_diff)

            self.assertEqual(expected_res, res)
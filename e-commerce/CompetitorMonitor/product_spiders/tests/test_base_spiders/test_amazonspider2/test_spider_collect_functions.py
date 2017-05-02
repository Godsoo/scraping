# -*- coding: utf-8 -*-
import unittest

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider


class TestAmazonSpiderCollectFunctions(unittest.TestCase):
    """
    Tests products collecting functions
    """
    def test_collect_all_returns_true_on_new_item(self):
        
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()
        items = [
            {'identifier': ":123", 'price': 1.0},
            {'identifier': ":234", 'price': 2.0},
            {'identifier': ":345", 'price': 3.0}
        ]
        new_item = {'identifier': ":456", 'price': 2.0}
        spider.collected_items = items[:]
        self.assertTrue(spider._collect_all(new_item))
        self.assertEqual(len(spider.collected_items), 4)
        self.assertEqual(spider.collected_items[-1]['identifier'], new_item['identifier'])

    def test_collect_all_returns_false_on_repeated_item(self):

        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()
        items = [
            {'identifier': ":123", 'price': 1.0},
            {'identifier': ":234", 'price': 2.0},
            {'identifier': ":345", 'price': 3.0}
        ]
        new_item = {'identifier': ":345", 'price': 2.0}
        spider.collected_items = items[:]
        self.assertFalse(spider._collect_all(new_item))
        self.assertEqual(len(spider.collected_items), 3)
        self.assertEqual(spider.collected_items[2]['price'], 2.0)

    def test_collect_lowest_new_item(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()
        items = []
        new_item = {'identifier': ":456", 'price': 2.0}
        spider.collected_items = items[:]
        spider._collect_lowest_price(new_item)
        self.assertIn(new_item, spider.collected_items)
        self.assertEqual(len(spider.collected_items), 1)
        self.assertEqual(spider.collected_items[0]['identifier'], new_item['identifier'])

    def test_collect_lowest_old_item_bigger_price(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()
        items = [
            {'identifier': ":123", 'price': 1.0},
        ]
        new_item = {'identifier': ":123", 'price': 3.5}
        spider.collected_items = items[:]
        spider._collect_lowest_price(new_item)
        self.assertNotIn(new_item, spider.collected_items)
        self.assertEqual(len(spider.collected_items), 1)
        self.assertEqual(spider.collected_items[0]['identifier'], items[0]['identifier'])

    def test_collect_lowest_old_item_smaller_price(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()
        items = [
            {'identifier': ":123", 'price': 2.0},
        ]
        new_item = {'identifier': ":234", 'price': 1.5}
        spider.collected_items = items[:]
        spider._collect_lowest_price(new_item)
        self.assertIn(new_item, spider.collected_items)
        self.assertEqual(len(spider.collected_items), 1)
        self.assertEqual(spider.collected_items[0]['identifier'], new_item['identifier'])

    def test_collect_best_match_new_item(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()
        items = []
        new_item = {'identifier': ":456", 'price': 2.0, 'name': 'Lego 123'}
        spider.collected_items = items[:]
        spider._collect_best_match(new_item, "Lego 123")
        self.assertIn(new_item, spider.collected_items)
        self.assertEqual(len(spider.collected_items), 1)
        self.assertEqual(spider.collected_items[0]['identifier'], new_item['identifier'])

    def test_collect_best_match_worse_match(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()
        items = [{'identifier': ":456", 'price': 2.0, 'name': 'Lego house 12'}]
        new_item = {'identifier': ":123", 'price': 1.0, 'name': 'Lego 12'}
        spider.collected_items = items[:]
        spider._collect_best_match(new_item, "Lego house 123")

        self.assertNotIn(new_item, spider.collected_items)
        self.assertEqual(len(spider.collected_items), 1)
        self.assertEqual(spider.collected_items[0]['identifier'], items[0]['identifier'])

    def test_collect_best_match_same_score(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()
        items = [{'identifier': ":456", 'price': 2.0, 'name': 'Lego house'}]
        new_item = {'identifier': ":123", 'price': 1.0, 'name': 'Lego 123'}
        spider.collected_items = items[:]
        spider._collect_best_match(new_item, "Lego house 123")
        self.assertNotIn(new_item, spider.collected_items)
        self.assertEqual(len(spider.collected_items), 1)
        self.assertEqual(spider.collected_items[0]['identifier'], items[0]['identifier'])

    def test_collect_best_match_better_match(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()
        items = [{'identifier': ":456", 'price': 2.0, 'name': 'Lego 12'}]
        new_item = {'identifier': ":123", 'price': 1.0, 'name': 'Lego house 12'}
        spider.collected_items = items[:]
        spider._collect_best_match(new_item, "Lego house 123")
        self.assertIn(new_item, spider.collected_items)
        self.assertEqual(len(spider.collected_items), 1)
        self.assertEqual(spider.collected_items[0]['identifier'], new_item['identifier'])
# -*- coding: utf-8 -*-
import unittest
from decimal import Decimal

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider


class TestAmazonSpiderConstructProduct(unittest.TestCase):
    def test_fills_in_all_necessary_fields(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()

        item = {
            'name': 'Item',
            'brand': 'brand',
            'identifier': 'ident',
            'price': '10.5',
            'url': 'product_url',
            'image_url': 'image_url',
            'sku': 'SKU',
            'shipping_cost': Decimal('22.5')
        }

        result_item = spider.construct_product(item)

        for field, value in item.items():
            self.assertIn(field, result_item.keys())
            if field == 'price':
                self.assertEqual(result_item[field], Decimal(value))
            elif field == 'identifier':
                self.assertEqual(result_item[field], ':' + value)
            elif field == 'url':
                continue
            else:
                if field == 'sku':
                    value = value.lower()
                self.assertEqual(result_item[field], value)

    def test_ignores_unknown_fields(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()

        item = {
            'name': 'Item',
            'brand': 'brand',
            'identifier': 'ident',
            'price': Decimal('10.5'),
            'url': 'product_url',
            'image_url': 'image_url',
            'sku': 'SKU',

            'some_cool_field': 'value'
        }

        result_item = spider.construct_product(item)

        self.assertNotIn('some_cool_field', result_item.keys())

    def test_works_with_minimum_set_of_fields(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()

        item = {
            'name': 'Item',
            'identifier': 'ident',
            'price': Decimal('10.5'),
            'url': 'product_url',
        }

        spider.construct_product(item)

    def test_fails_when_not_all_necessary_fields_provided(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()

        item = {
            'identifier': 'ident',
            'price': Decimal('10.5'),
            'sku': 'SKU',
        }

        self.assertRaises(KeyError, spider.construct_product, item)

    def test_works_when_price_is_none(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()

        item = {
            'name': 'Item',
            'identifier': 'ident',
            'price': None,
            'url': 'product_url',
        }

        spider.construct_product(item)

    def test_works_when_shipping_cost_is_none(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()

        item = {
            'name': 'Item',
            'identifier': 'ident',
            'price': Decimal('10.5'),
            'url': 'product_url',
            'shipping_cost': None
        }

        spider.construct_product(item)

    def test_fills_in_search_item_data_in_emtpy_fields(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()

        item = {
            'name': 'Item',
            'identifier': 'ident',
            'price': Decimal('10.5'),
            'url': 'product_url',
        }

        search_item = {
            'name': 'Item',
            'price': Decimal('13.3'),
            'sku': 'SKU',
            'category': 'cat',
            'brand': 'Brand'
        }

        spider.current_search_item = search_item

        result_item = spider.construct_product(item)

        self.assertEqual(result_item.get('sku'), search_item['sku'].lower())
        self.assertEqual(result_item.get('category'), search_item['category'])
        self.assertEqual(result_item.get('brand'), search_item['brand'])

    def test_transforms_price(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()

        spider.transform_price = lambda price: price * 10

        item = {
            'name': 'Item',
            'identifier': 'ident',
            'price': Decimal('10.5'),
            'url': 'product_url',
        }

        result_item = spider.construct_product(item)

        self.assertEqual(result_item.get('price'), item['price'] * 10)

    def test_ignores_model_if_not_enabled(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()
        spider.model_as_sku = False

        item = {
            'name': 'Item',
            'identifier': 'ident',
            'price': Decimal('10.5'),
            'url': 'product_url',
            'model': 'some_model'
        }

        res = spider.construct_product(item)

        self.assertTrue(res.get('sku') is None)

    def test_uses_model_if_enabled(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
        spider = Spider()
        spider.model_as_sku = True

        item = {
            'name': 'Item',
            'identifier': 'ident',
            'price': Decimal('10.5'),
            'url': 'product_url',
            'model': 'some_model'
        }

        res = spider.construct_product(item)

        self.assertEqual(res.get('sku'), item['model'])

    def test_uses_category_from_meta_category_type(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
            type = 'category'
        spider = Spider()

        item = {
            'name': 'Item',
            'identifier': 'ident',
            'price': Decimal('10.5'),
            'url': 'product_url',
            'model': 'some_model'
        }

        res = spider.construct_product(item, meta={'category': 'cat'})

        self.assertEqual(res.get('category'), 'cat')

    def test_uses_category_from_spider_attr_category_type(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
            type = 'category'
        spider = Spider()
        spider.current_category = 'cat'

        item = {
            'name': 'Item',
            'identifier': 'ident',
            'price': Decimal('10.5'),
            'url': 'product_url',
            'model': 'some_model'
        }

        res = spider.construct_product(item)

        self.assertEqual(res.get('category'), 'cat')

    def test_prefers_category_from_meta_over_spider_attr_category_type(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
            type = 'category'
        spider = Spider()
        spider.current_category = 'cat_attr'

        item = {
            'name': 'Item',
            'identifier': 'ident',
            'price': Decimal('10.5'),
            'url': 'product_url',
            'model': 'some_model'
        }

        res = spider.construct_product(item, meta={'category': 'cat_meta'})

        self.assertEqual(res.get('category'), 'cat_meta')

    def test_ignores_category_non_category_type(self):
        class Spider(BaseAmazonSpider):
            name = "Test Spider"
            domain = 'amazon.com'
            type = 'search'
        spider = Spider()
        spider.current_category = 'cat_attr'

        item = {
            'name': 'Item',
            'identifier': 'ident',
            'price': Decimal('10.5'),
            'url': 'product_url',
            'model': 'some_model'
        }

        res = spider.construct_product(item, meta={'category': 'cat_meta'})

        self.assertEqual(res.get('category'), '')

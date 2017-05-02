import unittest

from ..hashing import ProductHash
from mock import MagicMock


class TestProductHash(unittest.TestCase):
    def test_same_hash(self):
        first = {'identifier': '111', 'name': 'Product 1 ', 'sku': 'sku 111',
                 'brand': 'brand', 'category': 'category', 'url': 'url 111', 'dealer': 'dealer'}

        second = {'identifier': '222', 'name': 'product 1', 'sku': 'sku 222',
                  'brand': 'brand', 'category': 'category', 'url': 'url 222', 'dealer': 'dealer'}
        product_hash = ProductHash()
        self.assertEqual(product_hash.hash(first), product_hash.hash(second))

    def test_hash_differs(self):
        first = {'identifier': '111', 'name': 'Product 1 ', 'sku': 'sku 111',
                 'brand': 'brand', 'category': 'category', 'url': 'url 111', 'dealer': 'dealer'}

        second = {'identifier': '222', 'name': 'product 2', 'sku': 'sku 222',
                  'brand': 'brand', 'category': 'category', 'url': 'url 222', 'dealer': 'dealer'}
        product_hash = ProductHash()
        self.assertNotEqual(product_hash.hash(first), product_hash.hash(second))
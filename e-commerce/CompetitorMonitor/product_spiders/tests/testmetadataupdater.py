import sys
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append('..')
sys.path.append(os.path.abspath(os.path.join(HERE,
                                             '../../productspidersweb')))

from productspidersweb.models import *

from productsupdater.metadataupdater import MetadataUpdater

class TestMetadataUpdater(unittest.TestCase):

    def test_simple_review_add(self):
        m = MetadataUpdater({})
        old = {'reviews': []}
        new = {'reviews': [{'sku': '1', 'rating': '4', 'full_text': 'text', 'date': '02/02/2014'}]}
        res = m.get_changes(old, new)

        self.assertEqual(len(res['insert']), 1)
        self.assertEqual(len(res['delete']), 0)
        self.assertEqual(len(res['update']), 0)

    def test_simple_review_add_second(self):
        m = MetadataUpdater({})
        old = {'reviews': [{'sku': '1', 'rating': '4', 'full_text': 'text', 'date': '02/02/2014'}]}
        new = {'reviews': [
            {'sku': '1', 'rating': '4', 'full_text': 'text', 'date': '02/02/2014'},
            {'sku': '1', 'rating': '3', 'full_text': 'text 2', 'date': '03/02/2014'},
        ]}
        res = m.get_changes(old, new)

        self.assertEqual(len(res['insert']), 1)
        self.assertEqual(len(res['delete']), 0)
        self.assertEqual(len(res['update']), 0)

    def test_simple_review_update(self):
        m = MetadataUpdater({})
        old = {'reviews': [{'sku': '1', 'rating': '5', 'full_text': 'text',  'date': '02/02/2014'}]}
        new = {'reviews': [{'sku': '1', 'rating': '4', 'full_text': 'text',  'date': '02/02/2014'}]}
        res = m.get_changes(old, new)

        self.assertEqual(len(res['insert']), 1)
        self.assertEqual(len(res['delete']), 1)

    def test_simple_review_update_with_id(self):
        m = MetadataUpdater({})
        old = {'reviews': [{'sku': '1', 'rating': '4', 'full_text': 'text',  'date': '02/02/2014', 'review_id': '1'}]}
        new = {'reviews': [{'sku': '1', 'rating': '5', 'full_text': 'text',  'date': '02/02/2014', 'review_id': '1'}]}
        res = m.get_changes(old, new)
        self.assertEqual(len(res['insert']), 0)
        self.assertEqual(len(res['delete']), 0)

    def test_simple_review_update_with_one_id(self):
        m = MetadataUpdater({})
        old = {'reviews': [{'sku': '1', 'rating': '5', 'full_text': 'text',  'date': '02/02/2014'}]}
        new = {'reviews': [{'sku': '1', 'rating': '5', 'full_text': 'text',  'date': '02/02/2014', 'review_id': '1'}]}
        res = m.get_changes(old, new)
        self.assertEqual(len(res['insert']), 0)
        self.assertEqual(len(res['delete']), 0)

    def test_review_update_with_id_must_populate_update(self):
        m = MetadataUpdater({})
        old = {'reviews': [{'sku': '1', 'rating': '4', 'full_text': 'text',  'date': '02/02/2014', 'review_id': '1'}]}
        new = {'reviews': [{'sku': '1', 'rating': '5', 'full_text': 'text',  'date': '02/02/2014', 'review_id': '1'}]}
        res = m.get_changes(old, new)
        self.assertEqual(len(res['insert']), 0)
        self.assertEqual(len(res['delete']), 0)
        self.assertEqual(len(res['update']), 1)

        row = res['update'][0]

        self.assertEqual(row, {'field': 'reviews', 'value': new['reviews'][0]})

    def test_should_not_update_if_value_is_list_and_not_review(self):
        m = MetadataUpdater({})
        old = {'field': ['1', '2', '3']}
        new = {'field': ['1', '2', '3', '4']}
        res = m.get_changes(old, new)
        self.assertEqual(len(res['insert']), 0)
        self.assertEqual(len(res['delete']), 0)
        self.assertEqual(len(res['update']), 0)

    def test_simple_update(self):
        m = MetadataUpdater({})
        old = {'field': 'test'}
        new = {'field': 'test2'}
        res = m.get_changes(old, new)
        self.assertEqual(len(res['update']), 1)
        self.assertEqual(res['update'], [{'field': 'field', 'old_value': 'test', 'value': 'test2'}])
        self.assertEqual(res['new_metadata'], {'field': 'test2'})

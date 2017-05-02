import unittest

from ..join import SortedJoin, JoinFunction
import tempfile
import os
import csv
from mock import MagicMock


def _reader(path):
    f = open(path)
    reader = csv.DictReader(f)
    return reader


class TestSortedJoin(unittest.TestCase):
    def setUp(self):
        self.old_path = tempfile.mktemp()
        self.new_path = tempfile.mktemp()
        self.header = ['identifier', 'value']
        self.joined_rows = []
        self.join_func = lambda el_old, el_new: self.joined_rows.append([el_old, el_new])
        self.cmp_func = lambda el_old, el_new: cmp(el_old['identifier'], el_new['identifier'])

    def tearDown(self):
        if os.path.exists(self.old_path):
            os.remove(self.old_path)
        if os.path.exists(self.new_path):
            os.remove(self.new_path)

    def write_csv(self, path, lines):
        with open(path, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(self.header)
            for line in lines:
                writer.writerow(line)

    def get_sorted_join(self):
        return SortedJoin(_reader(self.old_path), _reader(self.new_path))

    def test_full_join_empty_files(self):
        self.write_csv(self.old_path, [])
        self.write_csv(self.new_path, [])
        s = self.get_sorted_join()
        s.full_join(self.join_func, self.cmp_func)
        self.assertEqual(self.joined_rows, [])

    def test_full_join_same_files(self):
        self.write_csv(self.old_path, [['1', 'v1'], ['2', 'v2']])
        self.write_csv(self.new_path, [['1', 'v1'], ['2', 'v2']])
        s = self.get_sorted_join()
        s.full_join(self.join_func, self.cmp_func)
        expected = [[{'identifier': '1', 'value': 'v1'}, {'identifier': '1', 'value': 'v1'}],
                    [{'identifier': '2', 'value': 'v2'}, {'identifier': '2', 'value': 'v2'}]]
        self.assertEqual(self.joined_rows, expected)

    def test_full_join_change_non_key(self):
        self.write_csv(self.old_path, [['1', 'v1'], ['2', 'v3']])
        self.write_csv(self.new_path, [['1', 'v1'], ['2', 'v5']])
        s = self.get_sorted_join()
        s.full_join(self.join_func, self.cmp_func)
        expected = [[{'identifier': '1', 'value': 'v1'}, {'identifier': '1', 'value': 'v1'}],
                    [{'identifier': '2', 'value': 'v3'}, {'identifier': '2', 'value': 'v5'}]]
        self.assertEqual(self.joined_rows, expected)

    def test_full_join_unmatched_rows(self):
        self.write_csv(self.old_path, [['1', 'v1'], ['3', 'v3'], ['5', 'v5']])
        self.write_csv(self.new_path, [['2', 'v2'], ['3', 'v3'], ['4', 'v4']])
        s = self.get_sorted_join()
        s.full_join(self.join_func, self.cmp_func)
        expected = [[{'identifier': '1', 'value': 'v1'}, None],
                    [None, {'identifier': '2', 'value': 'v2'}],
                    [{'identifier': '3', 'value': 'v3'}, {'identifier': '3', 'value': 'v3'}],
                    [None, {'identifier': '4', 'value': 'v4'}],
                    [{'identifier': '5', 'value': 'v5'}, None]]
        self.assertEqual(self.joined_rows, expected)

    def test_inner_join(self):
        self.write_csv(self.old_path, [['1', 'v1'], ['3', 'v3'], ['5', 'v5']])
        self.write_csv(self.new_path, [['2', 'v2'], ['3', 'v3'], ['4', 'v4']])
        s = self.get_sorted_join()
        s.inner_join(self.join_func, self.cmp_func)
        expected = [[{'identifier': '3', 'value': 'v3'}, {'identifier': '3', 'value': 'v3'}]]
        self.assertEqual(self.joined_rows, expected)


class TestJoinFunction(unittest.TestCase):
    def test_join_function(self):
        class update(object):
            pass

        updater1 = update()
        updater1.process_result = MagicMock(return_value=None)
        updater2 = update()
        updater2.process_result = MagicMock(return_value=None)

        join_f = JoinFunction(lambda x, y, z: (x, y), [updater1, updater2])
        join_f(1, 1)
        updater1.process_result.assert_called_once_with((1, 1))
        updater2.process_result.assert_called_once_with((1, 1))
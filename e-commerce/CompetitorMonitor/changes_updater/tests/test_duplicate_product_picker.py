# -*- coding: utf-8 -*-
import unittest
import tempfile
import csv
import os
import json

from ..duplicate_product_picker import remove_duplicates, remove_duplicates_meta, encode_row, decode_row


file_header = "identifier,sku,name,price,url,category,brand,image_url,shipping_cost,stock,dealer".split(',')


def write_products_to_tempfile(products):
    fo = tempfile.NamedTemporaryFile('w+', delete=False)
    with fo.file as f:
        writer = csv.DictWriter(f, fieldnames=file_header)
        if products:
            writer.writeheader()

        for prod in products:
            writer.writerow(encode_row(prod))

    fo.close()
    return fo.name


def read_products_from_file(filepath):
    with open(filepath) as f:
        reader = csv.DictReader(f)
        return [decode_row(row) for row in reader]


def write_products_to_tempfile_meta(products):
    fo = tempfile.NamedTemporaryFile('w+', delete=False)
    with fo.file as f:
        for prod in products:
            f.write(json.dumps(prod) + '\n')

    fo.close()
    return fo.name


def read_products_from_file_meta(filepath):
    with open(filepath) as f:
        return [json.loads(line) for line in f]


class TestDuplicateProductPicker(unittest.TestCase):
    def create_product(self, identifier, name, price, url, sku='', category='', brand='', image_url='',
                       shipping_cost='', stock='', dealer=''):
        return {
            'identifier': identifier,
            'name': name,
            'price': price,
            'url': url,
            'sku': sku,
            'category': category,
            'brand': brand,
            'image_url': image_url,
            'shipping_cost': shipping_cost,
            'stock': stock,
            'dealer': dealer
        }

    def check_duplicates_picker(self, input_products, expected_products, expected_dups_count):
        products_filepath = write_products_to_tempfile(input_products)
        duplicates_count = remove_duplicates(products_filepath)
        self.assertEqual(duplicates_count, expected_dups_count)
        res_products = read_products_from_file(products_filepath)
        self.assertEqual(sorted(res_products), sorted(expected_products))
        os.unlink(products_filepath)

    def test_no_duplicates(self):
        prod1 = self.create_product('id1', 'name1', '10', 'url1')
        prod2 = self.create_product('id2', 'name2', '20', 'url2')

        input_products = [prod1, prod2]
        expected_products = [prod1, prod2]
        expected_dups_count = 0

        self.check_duplicates_picker(input_products, expected_products, expected_dups_count)

    def test_one_duplicate(self):
        prod1 = self.create_product('id1', 'name1', '10', 'url1')
        prod11 = self.create_product('id1', 'name1', '9', 'url1')
        prod2 = self.create_product('id2', 'name2', '20', 'url2')

        input_products = [prod1, prod11, prod2]
        expected_products = [prod11, prod2]
        expected_dups_count = 1

        self.check_duplicates_picker(input_products, expected_products, expected_dups_count)

    def test_one_duplicate_2(self):
        prod1 = self.create_product('id1', 'name1', '12', 'url1')
        prod11 = self.create_product('id1', 'name1', '100', 'url1')
        prod2 = self.create_product('id2', 'name2', '20', 'url2')

        input_products = [prod1, prod11, prod2]
        expected_products = [prod1, prod2]
        expected_dups_count = 1

        self.check_duplicates_picker(input_products, expected_products, expected_dups_count)

    def test_two_duplicates_for_one_product(self):
        prod1 = self.create_product('id1', 'name1', '11', 'url1')
        prod11 = self.create_product('id1', 'name1', '12', 'url1')
        prod12 = self.create_product('id1', 'name1', '10', 'url1')
        prod2 = self.create_product('id2', 'name2', '20', 'url2')

        input_products = [prod1, prod11, prod12, prod2]
        expected_products = [prod12, prod2]
        expected_dups_count = 2

        self.check_duplicates_picker(input_products, expected_products, expected_dups_count)

    def test_takes_first_product_from_equal_price_dups(self):
        prod1 = self.create_product('id1', 'name1', '10', 'url1')
        prod11 = self.create_product('id1', 'name1', '10', 'url1')
        prod12 = self.create_product('id1', 'name1', '10', 'url1')
        prod2 = self.create_product('id2', 'name2', '20', 'url2')

        input_products = [prod1, prod11, prod12, prod2]
        expected_products = [prod1, prod2]
        expected_dups_count = 2

        self.check_duplicates_picker(input_products, expected_products, expected_dups_count)

    def test_one_duplicate_for_several_products(self):
        prod1 = self.create_product('id1', 'name1', '10', 'url1')
        prod11 = self.create_product('id1', 'name1', '11', 'url1')
        prod2 = self.create_product('id2', 'name2', '20', 'url2')
        prod21 = self.create_product('id2', 'name2', '2', 'url2')

        input_products = [prod1, prod11, prod2, prod21]
        expected_products = [prod1, prod21]
        expected_dups_count = 2

        self.check_duplicates_picker(input_products, expected_products, expected_dups_count)

    def test_different_names_are_not_duplicates(self):
        """
        It should not pick products with same identifier but different name as duplicate.
        These cases must be detected by update validator instead, as it's clearly issue with spider
        """
        prod1 = self.create_product('id1', 'name1', '12', 'url1')
        prod11 = self.create_product('id1', 'name11', '100', 'url1')
        prod2 = self.create_product('id2', 'name2', '20', 'url2')

        input_products = [prod1, prod11, prod2]
        expected_products = [prod1, prod11, prod2]
        expected_dups_count = 0

        self.check_duplicates_picker(input_products, expected_products, expected_dups_count)

    def test_different_names_are_not_duplicates_case_insensetive(self):
        prod1 = self.create_product('id1', 'name1', '12', 'url1')
        prod11 = self.create_product('id1', 'Name1', '100', 'url1')
        prod2 = self.create_product('id2', 'name2', '20', 'url2')

        input_products = [prod1, prod11, prod2]
        expected_products = [prod1, prod2]
        expected_dups_count = 1

        self.check_duplicates_picker(input_products, expected_products, expected_dups_count)

    def test_two_sets_of_duplicates_one_identifier(self):
        prod1 = self.create_product('id1', 'name11', '19', 'url1')
        prod11 = self.create_product('id1', 'Name11', '102', 'url1')
        prod12 = self.create_product('id1', 'name1', '100', 'url1')
        prod13 = self.create_product('id1', 'name1', '12', 'url1')
        prod2 = self.create_product('id2', 'name2', '20', 'url2')

        input_products = [prod1, prod11, prod12, prod13, prod2]
        expected_products = [prod1, prod13, prod2]
        expected_dups_count = 2

        self.check_duplicates_picker(input_products, expected_products, expected_dups_count)

    def test_unicode(self):
        prod1 = self.create_product('id1', u'имя1', '10', 'url1')
        prod2 = self.create_product('id2', u'имя2', '20', 'url2')

        input_products = [prod1, prod2]
        expected_products = [prod1, prod2]
        expected_dups_count = 0

        self.check_duplicates_picker(input_products, expected_products, expected_dups_count)

    def test_no_products(self):
        self.check_duplicates_picker([], [], 0)


class TestDuplicateProductPickerMeta(TestDuplicateProductPicker):
    """
    Exactly the same tests but for meta
    """
    def create_product(self, identifier, name, price, url, sku='', category='', brand='', image_url='',
                       shipping_cost='', stock='', dealer=''):
        product = super(TestDuplicateProductPickerMeta, self).create_product(
            identifier, name, price, url, sku, category, brand, image_url, shipping_cost, stock, dealer)
        product['metadata'] = {'asd': 'qwe'}
        return product

    def check_duplicates_picker(self, input_products, expected_products, expected_dups_count):
        products_filepath = write_products_to_tempfile_meta(input_products)
        duplicates_count = remove_duplicates_meta(products_filepath)
        self.assertEqual(duplicates_count, expected_dups_count)
        res_products = read_products_from_file_meta(products_filepath)
        self.assertEqual(sorted(res_products), sorted(expected_products))
        os.unlink(products_filepath)

    def test_vertical_bar(self):
        prod1 = self.create_product('id1', 'name1 | 1', '10', 'url1')
        prod2 = self.create_product('id2', 'name2 | 2', '20', 'url2')

        input_products = [prod1, prod2]
        expected_products = [prod1, prod2]
        expected_dups_count = 0

        self.check_duplicates_picker(input_products, expected_products, expected_dups_count)

    def test_vertical_bar2(self):
        prod1 = self.create_product('id1', 'name1', '10', 'url1|1')
        prod2 = self.create_product('id2', 'name2', '20', 'url2|2')

        input_products = [prod1, prod2]
        expected_products = [prod1, prod2]
        expected_dups_count = 0

        self.check_duplicates_picker(input_products, expected_products, expected_dups_count)

    def test_vertical_bar3(self):
        prod1 = self.create_product('id1', 'name1', '10', 'url', dealer='asd | qwe')
        prod2 = self.create_product('id2', 'name2', '20', 'url', dealer='asd | qwe')

        input_products = [prod1, prod2]
        expected_products = [prod1, prod2]
        expected_dups_count = 0

        self.check_duplicates_picker(input_products, expected_products, expected_dups_count)

# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import csv
import json
from decimal import Decimal

from datafiles import sort_products_file, sort_metadata_file

from product_spiders.utils import remove_punctuation_and_spaces


def decode_row(row):
    res = {}
    for c in row:
        res[c] = row[c].decode('utf8')
    return res


def encode_row(row):
    res = {}
    for c in row:
        res[c] = row[c].encode('utf8')
    return res


def _get_product_key(product):
    """
    >>> a = {'name': 'Burgess Excel Tasty Nuggets for Adult Rabbits-4kg', 'identifier': '1928'}
    >>> b = {'name': 'Burgess Excel Tasty Nuggets for Adult Rabbits 4kg', 'identifier': '1928'}
    >>> res1 = _get_product_key(a)
    >>> res2 = _get_product_key(b)
    >>> res1 == res2
    True
    >>> res1
    ('1928', 'burgessexceltastynuggetsforadultrabbits4kg')
    """
    identifier = product['identifier']
    name = remove_punctuation_and_spaces(product['name']).lower()
    return identifier, name


def _hash_identifier_plus_name(product):
    identifier, name = _get_product_key(product)
    identifier = identifier.decode('utf-8') if isinstance(identifier, str) else identifier
    name = name.decode('utf-8') if isinstance(name, str) else name
    return u'{}:{}'.format(identifier, name).encode('utf-8')


def _process(prods_iter, read_func, write_func):
    duplicates_found = 0
    previous_product = None
    for row in prods_iter:
        product = read_func(row)
        # if first row - save it to prev row and advance
        if not previous_product:
            previous_product = product
            continue
        # if current row is the same product as previous row, substitute of price is lower
        if _get_product_key(product) == _get_product_key(previous_product):
            duplicates_found += 1
            if Decimal(product['price']) < Decimal(previous_product['price']):
                previous_product = product
            continue
        # write to writer only if identifier has changed
        if 'product_hash' in previous_product:
            del(previous_product['product_hash'])
        write_func(previous_product)
        previous_product = product

    if previous_product:
        if 'product_hash' in previous_product:
            del (previous_product['product_hash'])
        write_func(previous_product)
    return duplicates_found


def remove_duplicates(products_path):
    """
    The function processes file removing all duplicates (found using identifier+name)
    only leaving product with lowest price.

    Identifier + name is used instead of just identifier, because when different product have the same identifier
    then it's clearly an issue with spider and should be detected by validator

    """
    sorted_path = tempfile.mktemp()
    # sort products by identifier + name
    sort_products_file(products_path, sorted_path, hash_func=_hash_identifier_plus_name)
    with open(sorted_path) as f1:
        reader = csv.DictReader(f1)
        if not reader.fieldnames:
            for row in reader:
                raise ValueError("File header is missing in %s but there are records" % products_path)
            return 0
        fieldnames = reader.fieldnames[:]
        fieldnames.remove('product_hash')

        fo = tempfile.NamedTemporaryFile(mode='w', delete=False)
        with fo.file as f2:
            writer = csv.DictWriter(f2, fieldnames=fieldnames)

            writer.writeheader()

            duplicates_found = _process(reader, read_func=lambda row: decode_row(row),
                                        write_func=lambda product: writer.writerow(encode_row(product)))
        # close file so changes would be written to it
        fo.close()
        shutil.copy(fo.name, products_path)
        # remove temporary file before returning
        os.unlink(fo.name)

        return duplicates_found


def remove_duplicates_meta(meta_path):
    """
    The same as `remove_duplicates` but for meta
    """
    sorted_path = tempfile.mktemp()
    # sort products by identifier + name
    sort_metadata_file(meta_path, sorted_path, hash_func=_hash_identifier_plus_name)
    with open(sorted_path) as f1:
        fo = tempfile.NamedTemporaryFile(mode='w', delete=False)
        with fo.file as f2:
            duplicates_found = _process(f1,
                                        read_func=lambda row: json.loads(row, encoding='utf-8'),
                                        write_func=lambda product: f2.write(
                                            json.dumps(product, encoding='utf-8') + '\n'))
        # close file so changes would be written to it
        fo.close()
        shutil.copy(fo.name, meta_path)
        # remove temporary file before returning
        os.unlink(fo.name)

        return duplicates_found

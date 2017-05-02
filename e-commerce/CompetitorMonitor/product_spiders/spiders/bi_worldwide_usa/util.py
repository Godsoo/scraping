# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import os.path
import csv
import xlrd

import paramiko

from product_spiders.utils import extract_price
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT


def download_feed(file_start_with='', downloaded_file_prefix='', root=None, file_extension='xlsx'):
    HERE = os.path.abspath(os.path.dirname(__file__))

    if root is None:
        root = HERE

    transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
    password = "p02SgdLU"
    username = "biw"
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    files = sftp.listdir_attr()

    last = get_last_file(file_start_with, files, file_extension)

    filename = downloaded_file_prefix + 'biw_products.' + file_extension
    file_path = os.path.join(root, filename)
    sftp.get(last.filename, file_path)

    return file_path


def get_products_from_feed(file_start_with='', downloaded_file_prefix='', root=None, file_extension='xlsx'):
    file_path = download_feed(file_start_with, downloaded_file_prefix, root, file_extension)

    identifiers = set()

    def get_field_value_from_feed(field_name, item):
        fields_mapping = {
            'sku': ('BI ProductID', 'BI UK ProductID'),
            'name': ('BI ProductName', 'BI UK ProductName'),
            'price': ('BI ListPrice', 'BI UK Delivered Price'),
            'model': ('BI Model', 'BI UK Model'),
            'brand': ('BI UK Brand', 'BI Brand')
        }

        if field_name in item:
            return item[field_name]

        if field_name in fields_mapping:
            for map in fields_mapping[field_name]:
                if map in item:
                    return item[map]
            raise KeyError("%s" % str(fields_mapping[field_name]))

        raise KeyError()

    if file_extension=='xlsx':
        csv_filepath = file_path.replace('.xlsx', '.csv')
        excel_to_csv(file_path, csv_filepath)
        file_path = csv_filepath

    with open(file_path) as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:

            identifier = get_field_value_from_feed('sku', row)

            if identifier.lower() in identifiers:
                continue

            identifiers.add(identifier.lower())

            product = {
                # 'sku': get_field_value_from_feed('sku', row),
                'name': unicode(get_field_value_from_feed('name', row), errors='ignore'),
                'price': extract_price(get_field_value_from_feed('price', row)),
            }

            brand = get_field_value_from_feed('brand', row)
            model = convert_value(get_field_value_from_feed('model', row))

            if not brand or not model:
                continue

            search_string = "%s %s" % (brand, model)
            yield search_string, product

def excel_to_csv(xls_filename, csv_filename):
    wb = xlrd.open_workbook(xls_filename)
    sh = wb.sheet_by_index(0)
    csv_file = open(csv_filename, 'wb')
    wr = csv.writer(csv_file, quoting=csv.QUOTE_ALL)

    for rownum in xrange(sh.nrows):
        wr.writerow([unicode(val).encode('utf8') for val in sh.row_values(rownum)])
    csv_file.close()

def get_last_file(start_with, files, file_extension):
    """
    Returns the most recent file, for the file name which starts with start_with

    :param start_with: the file name has this form start_with + date
    :param files: files list sftp.listdir_attr
    """
    last = None
    for f in files:
        if ((last == None and start_with in f.filename and
                 f.filename.endswith(file_extension)) or
                (start_with in f.filename and f.filename.endswith(file_extension) and
                         f.st_mtime > last.st_mtime)):
            last = f
    return last

def convert_value(value):
    try:
        result = str(float(value)).strip()
        if result.endswith('.0'):
            result = result.replace('.0', '')
    except:
        result = str(value).strip()
    return result

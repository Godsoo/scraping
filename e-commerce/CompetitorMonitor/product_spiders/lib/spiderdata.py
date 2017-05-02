# -*- coding: utf-8 -*-

"""
Class to interact with spider data

Original developer: Emiliano M. Rudenick <emr.frei@gmail.com>

"""

import os
import shutil
import csv
from pandas import read_csv
from product_spiders.db import Session
from product_spiders.config import DATA_DIR
from productspidersweb.models import Spider, Crawl


HERE = os.path.abspath(os.path.dirname(__file__))


class SpiderDataException(Exception):
    pass


class SpiderData(object):

    COPY_DIR = '/tmp'
    ALL_COLUMNS = [
        'identifier', 'sku',
 	'name', 'price', 'url',
 	'category', 'brand', 'image_url',
 	'shipping_cost', 'stock', 'dealer',
    ]

    def __init__(self, spider_name='', website_id=None, spider_id=None, data_dir=DATA_DIR, copy_dir=COPY_DIR):
        if (not spider_name) and (not website_id) and (not spider_id):
            raise SpiderDataException('You must indicate either of the following values: spider_name, website_id or spider_id')

        self._spider_name = spider_name

        try:
            self._spider_id = int(spider_id) if spider_id else None
        except ValueError:
            raise SpiderDataException('ERROR in `spider_id` value => The ID must be an integer, the value %s is not a valid integer' % spider_id)

        try:
            self._website_id = website_id if website_id else None
        except ValueError:
            raise SpiderDataException('ERROR in `website_id` value => The ID must be an integer, the value %s is not a valid integer' % website_id)

        if os.path.exists(data_dir):
            self.data_dir = data_dir
        else:
            raise SpiderDataException('ERROR in `data_dir` value => The path "%s" does not exist, please specify a valid directory path' % data_dir)

        if os.path.exists(copy_dir):
            self.copy_dir = copy_dir
        else:
            raise SpiderDataException('ERROR in `copy_dir` value => The path "%s" does not exist, please specify a valid directory path' % copy_dir)

        # Load on demand
        self._spider_dict = {}
        self._last_crawl_id = None
        self._prev_crawl_id = None

    """
    Return a dict with the Spider data contained or None
    """
    def _get_spider_as_dict(self):
        spider_db = None
        spider_dict = None

        db_session = Session()

        if self._spider_id:
            spider_db = db_session.query(Spider).get(self._spider_id)
        elif self._website_id:
            spider_db = db_session.query(Spider)\
                .filter(Spider.website_id == self._website_id)\
                .one_or_none()
        elif self._spider_name:
            spider_db = db_session.query(Spider)\
                .filter(Spider.name == self._spider_name)\
                .one_or_none()

        if spider_db:
            spider_dict = spider_db.serialize()

        db_session.close()

        return spider_dict

    @property
    def spider_dict(self):
        if not self._spider_dict:
            self._spider_dict = self._get_spider_as_dict()
        return self._spider_dict

    @property
    def spider_name(self):
        if not self._spider_name:
            if self.spider_dict:
                self._spider_name = self.spider_dict['name']
        return self._spider_name

    @property
    def spider_id(self):
        if not self._spider_id:
            spider = self._get_spider_as_dict()
            if spider:
                self._spider_id = spider['id']
        return self._spider_id

    @property
    def last_crawl_id(self):
        if not self._last_crawl_id:
            if self.spider_id:
                db_session = Session()
                last_crawl = db_session.query(Crawl.id)\
                    .filter(Crawl.spider_id == self.spider_id)\
                .order_by(Crawl.crawl_date.desc(),
                          Crawl.id.desc())\
                .limit(1)\
                .first()
                self._last_crawl_id = last_crawl.id if last_crawl else None
                db_session.close()
        return self._last_crawl_id

    @property
    def last_crawl_products_path(self):
        if self.last_crawl_id:
            return self.get_products_path_crawl_id(self.data_dir, self.last_crawl_id)
        return None

    @property
    def prev_crawl_id(self):
        if not self._prev_crawl_id:
            if self.spider_id and self.last_crawl_id:
                db_session = Session()
                prev_crawl = db_session.query(Crawl.id)\
                    .filter(Crawl.spider_id == self.spider_id,
                            Crawl.id != self.last_crawl_id)\
                .order_by(Crawl.crawl_date.desc(),
                          Crawl.id.desc())\
                .limit(1)\
                .first()
                self._prev_crawl_id = prev_crawl.id if prev_crawl else None
                db_session.close()
        return self._prev_crawl_id

    @property
    def prev_crawl_products_path(self):
        if self.prev_crawl_id:
            return self.get_products_path_crawl_id(self.data_dir, self.prev_crawl_id)
        return None

    """
    Return crawl products filename path or None if file does not exist and `check_exists` is True
    """
    @classmethod
    def get_products_path_crawl_id(cls, data_dir, crawl_id, check_exists=True):
        filename = '%s_products.csv' % crawl_id
        full_path = os.path.join(data_dir, filename)
        if check_exists and (not os.path.exists(full_path)):
            full_path = None
        return full_path

    """
    Get last crawl's data and return it as a DataFrame object

    You can indicate the columns to be loaded and the order of them.

    Optionaly you can indicate the field to use as index (position on list).
    It uses the `identifier` field by default.
    The index could be either a list of columns or an iterable too.

    If `copy_to_tmp` is True then the file will be copy to a local temp directory.
    This is the default behaviour.

    """
    def get_last_crawl_data_pandas(self, columns=ALL_COLUMNS, index=0, copy_to_tmp=True):
        if self.last_crawl_products_path:
            file_path = self.last_crawl_products_path
            if copy_to_tmp:
                file_path = os.path.join(self.copy_dir, file_path.split('/')[-1])
                shutil.copy(self.last_crawl_products_path, file_path)
            return read_csv(file_path,
                            usecols=columns, index_col=index)
        return None

    """
    Get last crawl's data and return a tuple with the file object and a DictReader object

    If `copy_to_tmp` is True then the file will be copy to a local temp directory.
    This is the default behaviour.
    """
    def get_last_crawl_data_reader(self, copy_to_tmp=True):
        if self.last_crawl_products_path:
            file_path = self.last_crawl_products_path
            if copy_to_tmp:
                file_path = os.path.join(self.copy_dir, file_path.split('/')[-1])
                shutil.copy(self.last_crawl_products_path, file_path)
            file_obj = open(file_path)
            return file_obj, csv.DictReader(file_obj)
        return None, None

    """
    Get previous crawl's data and return it as a DataFrame object

    You can indicate the columns to be loaded and the order of them.

    Optionaly you can indicate the field to use as index (position on list).
    It uses the `identifier` field by default.
    The index could be either a list of columns or an iterable too.

    If `copy_to_tmp` is True then the file will be copy to a local temp directory.
    This is the default behaviour.
    """
    def get_prev_crawl_data_pandas(self, columns=ALL_COLUMNS, index=0, copy_to_tmp=True):
        if self.prev_crawl_products_path:
            file_path = self.prev_crawl_products_path
            if copy_to_tmp:
                file_path = os.path.join(self.copy_dir, file_path.split('/')[-1])
                shutil.copy(self.prev_crawl_products_path, file_path)
            return read_csv(file_path,
                            usecols=columns, index_col=index)
        return None

    """
    Get previous crawl's data and return a tuple with the file object and a DictReader object

    If `copy_to_tmp` is True then the file will be copy to a local temp directory.
    This is the default behaviour.
    """
    def get_prev_crawl_data_reader(self, copy_to_tmp=True):
        if self.prev_crawl_products_path:
            file_path = self.prev_crawl_products_path
            if copy_to_tmp:
                file_path = os.path.join(self.copy_dir, file_path.split('/')[-1])
                shutil.copy(self.prev_crawl_products_path, file_path)
            file_obj = open(file_path)
            return file_obj, csv.DictReader(file_obj)
        return None, None

# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import csv
import shutil

import logging

from scrapy.spider import BaseSpider
from scrapy.http import Request

class SearchSpiderBase(BaseSpider):
    skip_first_row = False

    def _create_search_urls(self, row):
        raise NotImplementedError()

    def _create_meta(self, row):
        raise NotImplementedError()

    def _get_csv_filename(self):
        raise NotImplementedError()

    def _get_csv_copy_filename(self):
        raise NotImplementedError()

    def start_requests(self):
        if hasattr(self, 'make_csv_copy') and self.make_csv_copy:
            shutil.copy(self._get_csv_filename(), self._get_csv_copy_filename())
            filename = self._get_csv_copy_filename()
        else:
            filename = self._get_csv_filename()

        with open(filename) as f:
            reader = csv.DictReader(f)
            i = 0
            if hasattr(self, 'limit') and self.limit:
                limit = self.limit
            else:
                limit = 100
            for row in reader:
                if hasattr(self, 'debug') and self.debug:
                    if i >= limit:
                        break

                meta = self._create_meta(row)
                for url in self._create_search_urls(row):
                    yield Request(
                        url,
                        meta=meta,
                        dont_filter=True
                    )
                i += 1
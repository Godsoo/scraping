__author__ = 'juraseg'

import csv
import os
import shutil

import logging

from scrapy.spider import BaseSpider
from scrapy.http import Request

from utils import parse_shoemetro_result_name

HERE = os.path.abspath(os.path.dirname(__file__))

class SearchSpiderBase(BaseSpider):
    def _create_search_url(self, name, color, size):
        raise NotImplementedError()

    def start_requests(self):
        shutil.copy(os.path.join(HERE, 'shoemetroall.csv'),os.path.join(HERE, 'shoemetroall.csv.' + self.name + '.cur'))

        with open(os.path.join(HERE, 'shoemetroall.csv.' + self.name + '.cur')) as f:
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
                sku = row['sku']

                res = parse_shoemetro_result_name(row['name'])
                if not res:
                    logging.error("Match not found!!! %s" % row['name'])
                    continue
                (name, color, size) = res

                url = self._create_search_url(name, color, size)
                yield Request(
                    url,
                    meta={'sku': sku, 'original_name': row['name'], 'name': name, 'color': color, 'size': size},
                    dont_filter=True
                )
                i += 1
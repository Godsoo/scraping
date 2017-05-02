# -*- coding: utf-8 -*-
import os.path
import shutil

try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy import log

from bigsitemethodspider import SpiderRootPathMetaclass

from product_spiders.config import DATA_DIR


class PrimarySpider(BaseSpider):
    """
    Base class for spiders which export results for secondary spiders

    Mandatory fields:
    'csv_file' - name of file to save to, will be saved in spider's package folder
    'json_file' - name of metadata file to save to, will be saved in spider's package folder
    """
    __metaclass__ = SpiderRootPathMetaclass

    use_data_dir = False

    def __init__(self, *args, **kwargs):
        super(PrimarySpider, self).__init__(*args, **kwargs)

        if not hasattr(self, 'csv_file') or self.csv_file is None:
            msg = "Primary Spider issue: spider has no attribute 'csv_file'"
            log.err(msg)
            self.errors.append(msg)

        if not self.use_data_dir:
            self.crawl_results_file_path = os.path.join(self.root_path, self.csv_file)
        else:
            self.crawl_results_file_path = os.path.join(DATA_DIR, self.csv_file)

        dispatcher.connect(self.spider_closed, 'export_finished')

    def spider_closed(self, spider, reason):
        """
        On full run saves crawl results for future use if it's full run then.
        """
        if spider.name == self.name:
            shutil.copy(os.path.join(DATA_DIR, '%s_products.csv' % spider.crawl_id), self.crawl_results_file_path)
            if hasattr(self, 'json_file') and self.json_file:
                shutil.copy(os.path.join(DATA_DIR, 'meta/%s_meta.json-lines' % spider.crawl_id), os.path.join(self.root_path, self.json_file))

# -*- coding: utf-8 -*-
import inspect
import logging
import importlib

from scrapy.spider import BaseSpider
from scrapy import Spider
from scrapy.spiderloader import SpiderLoader
from scrapy.utils.spider import iter_spider_classes
from scrapy import log
from product_spiders.db_utils import load_spiders_db_data, load_spider_db_data
from scrapy.utils.misc import walk_modules
from product_spiders.custom_crawl_methods import CRAWL_METHODS


logger = logging.getLogger(__name__)


def log_msg(msg, level=log.DEBUG):
    msg = "[CustomCrawlMethod SpiderManager]: " + msg
    logger.log(level=level, msg=msg)

try:
    from product_spiders.base_spiders.scrapelyxpathspider import get_spider_cls as get_scrapely_spider_cls, \
        spcls_name as scrapely_spcls_name
except ImportError as e:
    log_msg("ERROR: Failed to import Scrapely spider: %s" % str(e))
    get_scrapely_spider_cls = None
    scrapely_spcls_name = None

special_spiders_cls_getters = {}
if get_scrapely_spider_cls is not None:
    special_spiders_cls_getters[scrapely_spcls_name] = get_scrapely_spider_cls


class CustomCrawlMethodSpiderManager(SpiderLoader):
    def __init__(self, settings):
        self.spiders_db_cache = None
        self.spider_modules = settings.getlist('SPIDER_MODULES')
        self._spiders = {}
        #super(CustomCrawlMethodSpiderManager, self).__init__(settings)

    def _get_spider_db_model(self, spider_name, load_joined=None):
        '''
        if not self.spiders_db_cache:
            self.spiders_db_cache = {x.name: x for x in load_spiders_db_data()}
        return self.spiders_db_cache.get(spider_name)
        '''
        return load_spider_db_data(spider_name, load_joined=load_joined)

    
    def list(self):
        """
        Return a list with the names of all spiders available in the project.
        """
        if not self._spiders:
            for name in self.spider_modules:
                for module in walk_modules(name):
                    self._load_spiders(module)
        
        return list(self._spiders.keys())
    
    def _load_spider(self, module, spider):
        for spcls in iter_spider_classes(module):
            spider_name = spcls.name
            if spider_name != spider:
                continue

            spmdl = self._get_spider_db_model(spcls.name, ['crawl_method2'])
            if spmdl and spmdl.crawl_method2 and spmdl.crawl_method2.crawl_method:
                new_spcls = self._configure_spider_class(spcls, spmdl)
                if new_spcls is not None and inspect.isclass(new_spcls) and (issubclass(new_spcls, BaseSpider) or
                                                                             issubclass(new_spcls, Spider)):
                    spcls = new_spcls
                    setattr(spcls, 'name', spider_name)

            self._spiders[spider_name] = spcls
            break

    def _configure_spider_class(self, spcls, spmdl):
        if not spmdl.crawl_method2 or not spmdl.crawl_method2.crawl_method:
            return
        sp_crawl_method = spmdl.crawl_method2.crawl_method
        if sp_crawl_method in CRAWL_METHODS:
            log_msg("Spider %s has crawl method %s" % (spcls.name, sp_crawl_method))
            make_func = CRAWL_METHODS[spmdl.crawl_method2.crawl_method]
            return make_func(spcls, spmdl)
        elif sp_crawl_method:
            log_msg("Invalid crawl method %s for spider %s. Ignoring" % (sp_crawl_method, spcls.name))
            return

    def load(self, spider_name):
        try:
            spider = load_spider_db_data(spider_name)
            if spider.module:
                mod = importlib.import_module(spider.module)
                log_msg('Found module path on cache')
                self._load_spider(mod, spider_name)
            else:
                for name in self.spider_modules:
                    for module in walk_modules(name):
                        self._load_spider(module, spider_name)
            
            return super(CustomCrawlMethodSpiderManager, self).load(spider_name)
        except KeyError:
            for cls_name, get_cls_func in special_spiders_cls_getters.items():
                spcls = get_cls_func(spider_name)
                if spcls is not None:
                    log_msg("Got spider for class %s: %s" %(cls_name, spider_name))
                    return spcls
            raise


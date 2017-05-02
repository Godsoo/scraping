# -*- coding: utf-8 -*-
from scrapy.downloadermiddlewares.httpcache import HttpCacheMiddleware as _HttpCacheMiddleware
from scrapy.exceptions import NotConfigured
from scrapy.utils.misc import load_object

import product_spiders.db
from product_spiders.downloadermiddleware import cache_storages
from productspidersweb.models import Spider


class HttpCacheMiddlewareEnablePerSpider(_HttpCacheMiddleware):
    def __init__(self, settings, stats):
        # should not call parent's __init__ as that configures from "HTTPCACHE_ENABLED" variable
        # while this class should configure from "HTTPCACHE_PER_SPIDER_ENABLED"
        if not settings.get('HTTPCACHE_PER_SPIDER_ENABLED'):
            raise NotConfigured("Disabled")

        if not settings.get('HTTPCACHE_STORAGE'):
            raise NotConfigured("Missing param 'HTTPCACHE_STORAGE'. Storage not configured")

        self.stats = stats
        self.policy = load_object(settings['HTTPCACHE_POLICY'])(settings)
        self.storage_class = settings['HTTPCACHE_STORAGE']
        self.ignore_missing = settings.get('HTTPCACHE_IGNORE_MISSING')
        # dispatcher.connect(self.spider_opened, signal=signals.spider_opened)
        # dispatcher.connect(self.spider_closed, signal=signals.spider_closed)
        self.use_cache = set()
        self.expiration_time = {}

        self.settings = settings

    def spider_opened(self, spider):
        db_session = product_spiders.db.Session()
        db_spider = db_session.query(Spider).filter(Spider.name == spider.name).one()
        if db_spider and db_spider.use_cache:
            try:
                if hasattr(db_spider, 'cache_storage') and db_spider.cache_storage:
                    storage_class = cache_storages[db_spider.cache_storage]['class']
                    self.storage = load_object(storage_class)(self.settings)
                    spider.log("%s: using spider configured cache storage: %s" % (self.__class__.__name__, storage_class))
                else:
                    self.storage = load_object(self.settings['HTTPCACHE_STORAGE'])(self.settings)
                    spider.log("%s: using default cache storage: %s" % (self.__class__.__name__, self.settings['HTTPCACHE_STORAGE']))
            except NotConfigured as e:
                # cache disabled on storage error
                spider.log("%s: cache disabled because of error: %s" % (self.__class__.__name__, str(e)))
                db_session.close()
                return
            super(HttpCacheMiddlewareEnablePerSpider, self).spider_opened(spider)
            self.use_cache.add(spider.name)
            spider._http_cache_enabled = True
            if hasattr(spider, 'cache_expiration'):
                self.expiration_time[spider.name] = spider.cache_expiration
                spider._http_cache_expiration_time = spider.cache_expiration
            elif hasattr(db_spider, 'cache_expiration') and db_spider.cache_expiration:
                self.expiration_time[spider.name] = db_spider.cache_expiration
                spider._http_cache_expiration_time = db_spider.cache_expiration
            spider.log("%s: cache enabled for spider %s" % (self.__class__.__name__, spider.name))
        else:
            spider.log("%s: cache disabled for spider %s" % (self.__class__.__name__, spider.name))
        db_session.close()

    def spider_closed(self, spider):
        if spider.name in self.use_cache:
            super(HttpCacheMiddlewareEnablePerSpider, self).spider_closed(spider)
            self.use_cache.remove(spider.name)

    def process_request(self, request, spider):
        if spider.name not in self.use_cache:
            return
        else:
            if request.meta.get('recache', False):
                # Do not read cached version, but allow saving response to cache
                return
            return super(HttpCacheMiddlewareEnablePerSpider, self).process_request(request, spider)

    def process_response(self, request, response, spider):
        if spider.name not in self.use_cache:
            return response
        else:
            return super(HttpCacheMiddlewareEnablePerSpider, self).process_response(request, response, spider)
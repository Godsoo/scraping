# -*- coding: utf-8 -*-
import unittest
import sys
import os.path
import random

from scrapy.settings import Settings
from scrapy.statscollectors import DummyStatsCollector
from scrapy.exceptions import NotConfigured
from scrapy.spider import BaseSpider

from product_spiders.downloadermiddleware.http_cache_per_spider import HttpCacheMiddlewareEnablePerSpider
from product_spiders.downloadermiddleware.http_cache_storage_redis_postgres import \
    RedisPostgresHttpCacheStorage
from product_spiders.downloadermiddleware.http_cache_storage_ssdb import SSDBHttpCacheStorage

db_uri = 'postsql://productspiders:productspiders@localhost:5432/spiders_http_cache'
redis_host = 'localhost'
redis_port = '6379'
ssdb_host = 'localhost'
ssdb_port = 8888
expiration_secs = 60 * 60 * 4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE,
                                             '../../productspidersweb')))

from productspidersweb.models import initialize_sql
from productspidersweb.models import Spider, Account

sys.path.append(os.path.abspath(os.path.join(HERE, '..')))

from productsupdater import ProductsUpdater
from productsupdater.metadataupdater import MetadataUpdater
sys.path.append('..')

engine = create_engine('sqlite:///:memory:')
Session = sessionmaker()


class CrawlerMock(object):
    pass


class TestHttpCacheNotConfiguredExceptions(unittest.TestCase):
    def setUp(self):
        self.crawler = CrawlerMock()

    def test_disabled_by_conf(self):
        settings = Settings({
            "HTTPCACHE_PER_SPIDER_ENABLED": False
        })

        self.crawler.settings = settings
        stats = DummyStatsCollector(self.crawler)

        self.assertRaises(NotConfigured, HttpCacheMiddlewareEnablePerSpider, settings=settings, stats=stats)

    def test_initializes_on_correct_conf(self):
        settings = Settings({
            "HTTPCACHE_PER_SPIDER_ENABLED": True,
            "HTTPCACHE_STORAGE": 'product_spiders.downloadermiddleware.http_cache_storage_redis_postgres.RedisPostgresHttpCacheStorage',

            "HTTPCACHE_EXPIRATION_SECS": expiration_secs,
            "HTTPCACHE_POSTGRES_DB_URI": db_uri,
            "HTTPCACHE_REDIS_HOST": redis_host,
            "HTTPCACHE_REDIS_PORT": redis_port
        })

        self.crawler.settings = settings
        stats = DummyStatsCollector(self.crawler)

        middleware = HttpCacheMiddlewareEnablePerSpider(settings=settings, stats=stats)


class TestRedisPostgresStorage(unittest.TestCase):
    def test_storage_initializes_on_correct_conf(self):
        settings = Settings({
            "HTTPCACHE_EXPIRATION_SECS": expiration_secs,
            "HTTPCACHE_POSTGRES_DB_URI": db_uri,
            "HTTPCACHE_REDIS_HOST": redis_host,
            "HTTPCACHE_REDIS_PORT": redis_port
        })

        storage = RedisPostgresHttpCacheStorage(settings=settings)

    def test_fails_on_wrong_pg_host(self):
        settings = Settings({
            "HTTPCACHE_EXPIRATION_SECS": expiration_secs,
            "HTTPCACHE_POSTGRES_DB_URI": 'postsql://productspiders:productspiders@spiders.server:5432/spiders_http_cache',
            "HTTPCACHE_REDIS_HOST": redis_host,
            "HTTPCACHE_REDIS_PORT": redis_port
        })

        self.assertRaises(NotConfigured, RedisPostgresHttpCacheStorage, settings=settings)

    def test_fails_on_wrong_pg_port(self):
        settings = Settings({
            "HTTPCACHE_EXPIRATION_SECS": expiration_secs,
            "HTTPCACHE_POSTGRES_DB_URI": 'postsql://productspiders:productspiders@localhost:5431/spiders_http_cache',
            "HTTPCACHE_REDIS_HOST": redis_host,
            "HTTPCACHE_REDIS_PORT": redis_port
        })

        self.assertRaises(NotConfigured, RedisPostgresHttpCacheStorage, settings=settings)

    def test_fails_on_wrong_pg_username(self):
        settings = Settings({
            "HTTPCACHE_EXPIRATION_SECS": expiration_secs,
            "HTTPCACHE_POSTGRES_DB_URI": 'postsql://productspiders2:productspiders@localhost:5432/spiders_http_cache',
            "HTTPCACHE_REDIS_HOST": redis_host,
            "HTTPCACHE_REDIS_PORT": redis_port
        })

        self.assertRaises(NotConfigured, RedisPostgresHttpCacheStorage, settings=settings)

    def test_fails_on_pg_database_does_not_exists(self):
        settings = Settings({
            "HTTPCACHE_EXPIRATION_SECS": expiration_secs,
            "HTTPCACHE_POSTGRES_DB_URI": 'postsql://productspiders:productspiders@localhost:5432/not_exists',
            "HTTPCACHE_REDIS_HOST": redis_host,
            "HTTPCACHE_REDIS_PORT": redis_port
        })

        self.assertRaises(NotConfigured, RedisPostgresHttpCacheStorage, settings=settings)

    def test_fails_on_pg_database_with_no_hstore(self):
        settings = Settings({
            "HTTPCACHE_EXPIRATION_SECS": expiration_secs,
            "HTTPCACHE_POSTGRES_DB_URI": 'postsql://productspiders:productspiders@localhost:5432/productspiders',
            "HTTPCACHE_REDIS_HOST": redis_host,
            "HTTPCACHE_REDIS_PORT": redis_port
        })

        self.assertRaises(NotConfigured, RedisPostgresHttpCacheStorage, settings=settings)

    def test_fails_on_pg_database_with_no_data_table(self):
        settings = Settings({
            "HTTPCACHE_EXPIRATION_SECS": expiration_secs,
            "HTTPCACHE_POSTGRES_DB_URI": 'postsql://productspiders:productspiders@localhost:5432/spiders_http_cache2',
            "HTTPCACHE_REDIS_HOST": redis_host,
            "HTTPCACHE_REDIS_PORT": redis_port
        })

        self.assertRaises(NotConfigured, RedisPostgresHttpCacheStorage, settings=settings)

    def test_fails_on_wrong_redis_host(self):
        settings = Settings({
            "HTTPCACHE_EXPIRATION_SECS": expiration_secs,
            "HTTPCACHE_POSTGRES_DB_URI": db_uri,
            "HTTPCACHE_REDIS_HOST": "google.com",
            "HTTPCACHE_REDIS_PORT": redis_port
        })

        self.assertRaises(NotConfigured, RedisPostgresHttpCacheStorage, settings=settings)

    def test_fails_on_wrong_redis_port(self):
        settings = Settings({
            "HTTPCACHE_EXPIRATION_SECS": expiration_secs,
            "HTTPCACHE_POSTGRES_DB_URI": db_uri,
            "HTTPCACHE_REDIS_HOST": redis_host,
            "HTTPCACHE_REDIS_PORT": '1111'
        })

        self.assertRaises(NotConfigured, RedisPostgresHttpCacheStorage, settings=settings)


class TestSSDBStorage(unittest.TestCase):
    def test_storage_initializes_on_correct_conf(self):
        settings = Settings({
            "HTTPCACHE_EXPIRATION_SECS": expiration_secs,
            "HTTPCACHE_SSDB_HOST": ssdb_host,
            "HTTPCACHE_SSDB_PORT": ssdb_port
        })

        storage = SSDBHttpCacheStorage(settings=settings)

    def test_fails_on_wrong_ssdb_host(self):
        settings = Settings({
            "HTTPCACHE_EXPIRATION_SECS": expiration_secs,
            "HTTPCACHE_SSDB_HOST": "123456.78",
            "HTTPCACHE_SSDB_PORT": ssdb_port
        })

        self.assertRaises(NotConfigured, SSDBHttpCacheStorage, settings=settings)

    def test_fails_on_wrong_ssdb_port(self):
        settings = Settings({
            "HTTPCACHE_EXPIRATION_SECS": expiration_secs,
            "HTTPCACHE_SSDB_HOST": ssdb_host,
            "HTTPCACHE_SSDB_PORT": '1111'
        })

        self.assertRaises(NotConfigured, SSDBHttpCacheStorage, settings=settings)


class TestHTTPCacheWithSpider(unittest.TestCase):
    def setUp(self):
        self.crawler = CrawlerMock()

        self.connection = engine.connect()
        self.trans = self.connection.begin()
        initialize_sql(engine)
        self.db_session = Session(bind=self.connection)

        self.products_updater = ProductsUpdater(self.db_session, MetadataUpdater())

        account = Account()
        account.member_id = 1
        account.enabled = True
        self.db_session.add(account)
        self.db_session.commit()

        self.account_id = account.id

        # monkey path product_spiders.db
        import product_spiders.db
        self.old_engine = product_spiders.db.engine
        self.old_Session = product_spiders.db.Session
        product_spiders.db.engine = engine
        product_spiders.db.Session = Session

    def tearDown(self):
        self.trans.rollback()
        self.db_session.close()
        self.connection.close()

        # monkey path product_spiders.db back
        import product_spiders.db
        product_spiders.db.engine = self.old_engine
        product_spiders.db.Session = self.old_Session

    def test_default_expiration(self):
        settings = Settings({
            "HTTPCACHE_PER_SPIDER_ENABLED": True,
            "HTTPCACHE_STORAGE": 'product_spiders.downloadermiddleware.http_cache_storage_redis_postgres.RedisPostgresHttpCacheStorage',

            "HTTPCACHE_EXPIRATION_SECS": expiration_secs,
            "HTTPCACHE_POSTGRES_DB_URI": db_uri,
            "HTTPCACHE_REDIS_HOST": redis_host,
            "HTTPCACHE_REDIS_PORT": redis_port
        })

        self.crawler.settings = settings
        stats = DummyStatsCollector(self.crawler)

        middleware = HttpCacheMiddlewareEnablePerSpider(settings=settings, stats=stats)

        for _ in xrange(0, 10):
            expiration = random.randint(0, 100000)

            db_spider = Spider()
            db_spider.account_id = self.account_id
            db_spider.name = 'some_spider'
            db_spider.use_cache = True
            db_spider.cache_expiration = expiration
            self.db_session.add(db_spider)
            self.db_session.commit()

            class SomeSpider(BaseSpider):
                name = db_spider.name

            some_spider = SomeSpider()

            middleware.spider_opened(some_spider)
            self.assertTrue(hasattr(some_spider, '_http_cache_expiration_time'))
            self.assertEqual(some_spider._http_cache_expiration_time, expiration)

            self.db_session.query(Spider).delete()

    def test_disabled_on_storage_error(self):
        settings = Settings({
            "HTTPCACHE_PER_SPIDER_ENABLED": True,
            "HTTPCACHE_STORAGE": 'product_spiders.downloadermiddleware.http_cache_storage_redis_postgres.RedisPostgresHttpCacheStorage',

            "HTTPCACHE_EXPIRATION_SECS": expiration_secs,
            "HTTPCACHE_POSTGRES_DB_URI": 'postsql://productspiders:productspiders@spiders.server:5432/spiders_http_cache',
            "HTTPCACHE_REDIS_HOST": redis_host,
            "HTTPCACHE_REDIS_PORT": redis_port
        })

        self.crawler.settings = settings
        stats = DummyStatsCollector(self.crawler)

        middleware = HttpCacheMiddlewareEnablePerSpider(settings=settings, stats=stats)

        for _ in xrange(0, 10):
            expiration = random.randint(0, 100000)

            db_spider = Spider()
            db_spider.account_id = self.account_id
            db_spider.name = 'some_spider2'
            db_spider.use_cache = True
            db_spider.cache_expiration = expiration
            self.db_session.add(db_spider)
            self.db_session.commit()

            class SomeSpider(BaseSpider):
                name = db_spider.name

            some_spider = SomeSpider()

            middleware.spider_opened(some_spider)
            self.assertNotIn(some_spider.name, middleware.use_cache)

            self.db_session.query(Spider).delete()


if __name__ == '__main__':
    unittest.main()

# -*- coding: utf-8 -*-
from __future__ import with_statement, print_function

import datetime
import json
import logging
import os.path
import sys
from time import time, sleep
from urlparse import urlparse

import psycopg2
import psycopg2.extras
import redis
from psycopg2 import DatabaseError
from scrapy.exceptions import NotConfigured
from scrapy.http import Headers
from scrapy.responsetypes import responsetypes
from scrapy.utils.request import request_fingerprint
from w3lib.http import headers_raw_to_dict, headers_dict_to_raw


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE, '../productspidersweb')))


def parse_db_uri(db_uri):
    u = urlparse(db_uri)

    host = u.hostname
    port = u.port
    user = u.username
    password = u.password
    database_name = u.path[1:]
    return host, port, user, password, database_name


class StorageException(Exception):
    pass


class RedisPostgresHttpCacheStorage(object):
    def __init__(self, settings, stats=None):
        missing_params = []
        for param in ['HTTPCACHE_EXPIRATION_SECS', 'HTTPCACHE_POSTGRES_DB_URI', 'HTTPCACHE_REDIS_HOST',
                      'HTTPCACHE_REDIS_PORT']:
            if not settings.get(param):
                missing_params.append(param)
        if missing_params:
            raise NotConfigured("Can't initialize storage, missing params: %s" % ",".join(missing_params))

        self.expiration_secs = settings.getint('HTTPCACHE_EXPIRATION_SECS')

        self.db_uri = settings['HTTPCACHE_POSTGRES_DB_URI']
        try:
            host, port, user, password, database = parse_db_uri(self.db_uri)
        except ValueError:
            raise NotConfigured("Error parsing database connection URI: %s" % self.db_uri)
        try:
            self.db = psycopg2.connect(host=host, port=port, user=user, password=password, database=database)
            # to avoid "idle in transaction", check http://initd.org/psycopg/docs/faq.html for more information
            self.db.autocommit = True
        except psycopg2.OperationalError as e:
            raise NotConfigured("Error connecting to database using URI '%s': %s" %
                                (self.db_uri, str(e)))

        try:
            psycopg2.extras.register_hstore(self.db)
            self.cursor = self.db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            try:
                self.cursor.execute("SELECT * FROM http_cache_binary LIMIT 1")
            except DatabaseError:
                self.db.rollback()
                self.cursor.execute("SELECT * FROM http_cache_binary LIMIT 1")
        except psycopg2.ProgrammingError as e:
            raise NotConfigured("Error while initializing database %s: %s" %
                                (database, str(e)))

        self.redis_host = settings['HTTPCACHE_REDIS_HOST']
        self.redis_port = settings['HTTPCACHE_REDIS_PORT']
        self.redis_conn = redis.StrictRedis(host=self.redis_host, port=self.redis_port, socket_timeout=2)

        try:
            self.redis_conn.ping()
        except redis.ConnectionError as e:
            raise NotConfigured("Can't establish connection to redis server using host %s and port %s. Error: %s" %
                                (self.redis_host, self.redis_port, str(e)))

    def open_spider(self, spider):
        pass

    def close_spider(self, spider):
        pass

    def retrieve_response(self, spider, request):
        """Return response if present in cache, or None otherwise."""
        key = self._get_request_key(spider, request)

        expiration_time = self._get_expiration_time(spider)
        metadata = self._read_meta(key, expiration_time)
        if metadata is None:
            return  # not cached
        spider.log("%s: found cache for %s" % (self.__class__.__name__, request.url))

        res = self._get_cached_data(key, spider)

        if res is None:
            return None

        spider.log("%s: got response from cache for %s" % (self.__class__.__name__, request.url))

        response_url = res['response_url']
        response_body = str(res['response_body'])
        response_rawheaders = res['response_meta']['headers']
        status = res['response_meta']['status']
        response_headers = Headers(headers_raw_to_dict(response_rawheaders))
        response_cls = responsetypes.from_args(headers=response_headers, url=response_url)
        response = response_cls(url=response_url, headers=response_headers, status=status, body=response_body)
        return response

    def store_response(self, spider, request, response):
        """Store the given response in the cache."""
        spider.log("%s: storing cache for %s" % (self.__class__.__name__, request.url))

        self._save_cache_meta(spider, request, response)

        try:
            has_cache = self._check_cache_in_db(spider, request, response)
        except StorageException:
            return
        if has_cache:
            self._update_cache(spider, request, response)
        else:
            self._save_cache(spider, request, response)

    def _get_cached_data(self, key, spider):
        try:
            self.cursor.execute("SELECT * FROM http_cache_binary WHERE hashkey=%s", (key,))
        except DatabaseError:
            self.db.rollback()
            self.cursor.execute("SELECT * FROM http_cache_binary WHERE hashkey=%s", (key,))
        res = self.cursor.fetchone()
        # if just being saved to db by other spider
        tries = 5
        try_num = 0
        while not res:
            sleep(0.2)
            if try_num >= tries:
                self._clear_cache(key)
                spider.log("Error loading data for: %s" % key)
                res = None
                break
            try:
                self.cursor.execute("SELECT * FROM http_cache_binary WHERE hashkey=%s", (key,))
            except DatabaseError:
                self.db.rollback()
                self.cursor.execute("SELECT * FROM http_cache_binary WHERE hashkey=%s", (key,))
            res = self.cursor.fetchone()
            try_num += 1
        return res

    def _get_expiration_time(self, spider):
        if hasattr(spider, '_http_cache_expiration_time'):
            expiration_time = spider._http_cache_expiration_time
        else:
            expiration_time = None
        return expiration_time

    def _get_request_key(self, spider, request):
        return request_fingerprint(request)

    def _read_meta(self, key, expiration_time=None):
        if expiration_time is None:
            expiration_time = self.expiration_secs
        metadata = self.redis_conn.get(key)
        if not metadata:
            return  # not found
        try:
            metadata = json.loads(metadata)
        except ValueError:
            return None
        if 0 < expiration_time < time() - metadata['timestamp']:
            return  # expired
        return metadata

    def _clear_cache(self, key):
        self.redis_conn.delete(key)

    def _save_cache_meta(self, spider, request, response):
        key = self._get_request_key(spider, request)

        metadata = {
            'url': request.url,
            'method': request.method,
            'status': response.status,
            'response_url': response.url,
            'timestamp': time(),
        }
        self.redis_conn.set(key, json.dumps(metadata))

    def _update_cache(self, spider, request, response):
        key = self._get_request_key(spider, request)
        request_meta = {
            'headers': headers_dict_to_raw(request.headers),
            'method': request.method
        }

        response_meta = {
            'headers': headers_dict_to_raw(response.headers),
            'status': str(response.status)  # this is needed to make all values of str type
        }
        try:
            query = """
                UPDATE http_cache_binary
                SET ts=%(ts)s,
                request_url=%(request_url)s,
                request_meta=%(request_meta)s,
                request_body=%(request_body)s,
                response_url=%(response_url)s,
                response_meta=%(response_meta)s,
                response_body=%(response_body)s
                WHERE hashkey=%(hashkey)s
            """
            data = {
                'hashkey': key,
                'ts': datetime.datetime.now(),
                'request_url': request.url,
                'request_meta': request_meta,
                'request_body': psycopg2.Binary(request.body),
                'response_url': response.url,
                'response_meta': response_meta,
                'response_body': psycopg2.Binary(response.body)
            }
            self.cursor.execute(query, data)
        except DatabaseError, e:
            self.db.rollback()
            err = "[HTTP Cache] Error: failed to update cache in database: %s" % str(e)
            logging.error(err)
            if not hasattr(spider, 'errors'):
                spider.errors = []
            spider.errors.append('HTTP Cache failed. Please contact Yuri <yuri@competitormonitor.com>')
        else:
            self.db.commit()

    def _save_cache(self, spider, request, response):
        key = self._get_request_key(spider, request)
        request_meta = {
            'headers': headers_dict_to_raw(request.headers),
            'method': request.method
        }

        response_meta = {
            'headers': headers_dict_to_raw(response.headers),
            'status': str(response.status)  # this is needed to make all values of str type
        }
        try:
            query = """
                INSERT INTO http_cache_binary
                (hashkey, ts, request_url, request_meta, request_body,
                response_url, response_meta, response_body)
                VALUES
                (%(hashkey)s, %(ts)s, %(request_url)s, %(request_meta)s, %(request_body)s,
                %(response_url)s, %(response_meta)s, %(response_body)s)
            """
            data = {
                'hashkey': key,
                'ts': datetime.datetime.now(),
                'request_url': request.url,
                'request_meta': request_meta,
                'request_body': psycopg2.Binary(request.body),
                'response_url': response.url,
                'response_meta': response_meta,
                'response_body': psycopg2.Binary(response.body)
            }
            self.cursor.execute(query, data)
        except DatabaseError, e:
            self.db.rollback()
            err = "[HTTP Cache] Error: failed to save cache to database: %s" % str(e)
            if 'duplicate' not in err.lower():  # ignore 'duplicate' key errors
                logging.error(err)
                if not hasattr(spider, 'errors'):
                    spider.errors = []
                spider.errors.append('HTTP Cache failed. Please contact Yuri <yuri@competitormonitor.com>')
        else:
            self.db.commit()

    def _check_cache_in_db(self, spider, request, response):
        key = self._get_request_key(spider, request)
        try:
            self.cursor.execute("SELECT * FROM http_cache_binary WHERE hashkey=%s", (key, ))
        except DatabaseError:
            self.db.rollback()
            err = "[HTTP Cache] Error: failed to load cache from database"
            logging.error(err)
            if not hasattr(spider, 'errors'):
                spider.errors = []
            spider.errors.append(err)
            raise StorageException("Database error")
        res = self.cursor.fetchone()
        return bool(res)
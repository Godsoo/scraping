# -*- coding: utf-8 -*-
from __future__ import with_statement, print_function

import os.path
import sys
from time import time
import logging

import ssdb
from scrapy.exceptions import NotConfigured
from scrapy.http import Headers
from scrapy.responsetypes import responsetypes
from scrapy.utils.request import request_fingerprint
from w3lib.http import headers_raw_to_dict, headers_dict_to_raw


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE, '../productspidersweb')))


class StorageException(Exception):
    pass


class SSDBHttpCacheStorage(object):
    def __init__(self, settings, stats=None):
        missing_params = []
        for param in ['HTTPCACHE_EXPIRATION_SECS', 'HTTPCACHE_SSDB_HOST',
                      'HTTPCACHE_SSDB_PORT']:
            if not settings.get(param):
                missing_params.append(param)
        if missing_params:
            raise NotConfigured("Can't initialize storage, missing params: %s" % ",".join(missing_params))

        self.expiration_secs = settings.getint('HTTPCACHE_EXPIRATION_SECS')

        self.ssdb_host = settings['HTTPCACHE_SSDB_HOST']
        self.ssdb_port = settings['HTTPCACHE_SSDB_PORT']

        try:
            self.ssdb = ssdb.SSDB(host=self.ssdb_host, port=self.ssdb_port)
            self.ssdb.get('asd')
        except ssdb.ConnectionError as e:
            raise NotConfigured("Can't establish connection to SSDB server using host %s and port %s. Error: %s" %
                                (self.ssdb_host, self.ssdb_port, str(e)))

    def open_spider(self, spider):
        pass

    def close_spider(self, spider):
        pass

    def retrieve_response(self, spider, request):
        """Return response if present in cache, or None otherwise."""
        key = self._get_request_key(spider, request)

        expiration_time = self._get_expiration_time(spider)
        data = self._get_cache(key, spider, expiration_time)
        if data is None:
            logging.info("No cache for: %s" % key)
            return  # not cached
        spider.log("%s: found cache for %s" % (self.__class__.__name__, request.url))

        response_url = data['response_url']
        response_body = str(data['response_body'])
        response_rawheaders = data['response_meta']['headers']
        status = data['response_meta']['status']
        response_headers = Headers(headers_raw_to_dict(response_rawheaders))
        response_cls = responsetypes.from_args(headers=response_headers, url=response_url)
        response = response_cls(url=response_url, headers=response_headers, status=status, body=response_body)
        return response

    def store_response(self, spider, request, response):
        """Store the given response in the cache."""
        spider.log("%s: storing cache for %s" % (self.__class__.__name__, request.url))

        self._save_cache(spider, request, response)

    def _get_expiration_time(self, spider):
        if hasattr(spider, '_http_cache_expiration_time'):
            expiration_time = spider._http_cache_expiration_time
        else:
            expiration_time = None
        return expiration_time

    def _get_request_key(self, spider, request):
        return request_fingerprint(request)

    def _get_cache(self, key, spider, expiration_time):
        if expiration_time is None:
            expiration_time = self.expiration_secs
        data = self.ssdb.get(key)
        if not data:
            logging.info("No data found for: %s" % key)
            return  # not found
        try:
            data = eval(data)
        except (ValueError, KeyError, TypeError, NameError):
            logging.error("Error eval-ing: %s" % key)
            return None

        if 0 < expiration_time < time() - data['ts']:
            logging.error("Expired: %s" % key)
            return  # expired
        return data

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
        data = {
            'hashkey': key,
            'ts': time(),
            'request_url': request.url,
            'request_meta': request_meta,
            'request_body': bytearray(request.body),
            'response_url': response.url,
            'response_meta': response_meta,
            'response_body': bytearray(response.body)
        }
        self.ssdb.setx(key, data, self.expiration_secs)

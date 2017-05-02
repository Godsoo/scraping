# -*- coding: utf-8 -*-
'''
    BaseGoogleSpider
    ~~~~~~~~~~~~~~
    
    A base spider for Google API
    
'''

__autor__ = 'Emiliano M. Rudenick'


import os
import logging

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.exceptions import CloseSpider

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))


class BaseGoogleSpider(BaseSpider):

    handle_httpstatus_list = [403, 400, 503]

    KEYS = []

    KEYS_FILE = 'googleapikeys.txt'

    def __init__(self, *args, **kwargs):
        super(BaseGoogleSpider, self).__init__(*args, **kwargs)
        self._url = 'https://www.googleapis.com/shopping/search/v1/public/' + \
            'products?key=%(key)s&country=GB&q=%(search)s&restrictBy=condition=new'
        self._init_keys()
        self._init_items()
        self._retry_items = set()
        self._meta_fields = self._get_meta_fields()
        self._format_fields = self._get_format_fields()

    def _get_items(self):
        raise NotImplementedError

    def _get_api_keys(self):
        keys = self.KEYS
        if not keys:
            try:
                with open(os.path.join(HERE, self.KEYS_FILE)) as f:
                    for line in f:
                        keys.append(line.strip())
            except:
                log.msg('Could not get the keys from file!', level=log.ERROR)
                raise CloseSpider('ERROR')
        return keys

    def _get_current_key_index(self):
        if self._current_key_index >= len(self._api_keys):
            self._current_key_index = 0
        return self._current_key_index

    def _get_key(self):
        current_key = self._get_current_key_index()
        if self._api_keys:
            return self._api_keys[current_key]
        return None

    def _get_meta_fields(self):
        # [('sku', 'SKU'), ('name', 'Title')]
        return []

    def _get_format_fields(self):
        # [('price', self._func_format_price)]
        return []

    def _init_keys(self):
        self._current_key_index = 0
        self._api_keys = self._get_api_keys()

    def _init_items(self):
        self._items = self._get_items()

    def _create_search_url(self, key, item):
        try:
            search = item['name']
            return self._url % ({'key': key, 'search': search})
        except:
            raise NotImplementedError

    def _api_search(self, *args, **kwargs):

        key = kwargs.get('key', self._get_key())
        items = kwargs.get('items', self._get_items())
        item = kwargs.get('item', None)

        try:
            if item is None:
                item = items.next()
        except StopIteration:
            self.log('No item found')
            return

        for field, func_format in self._format_fields:
            item[field] = func_format(item[field])

        self.log('ITEM: %s | Using KEY: %s' % (item, key))

        meta = dict(dict((m_k, item[m_f]) for m_k, m_f in self._meta_fields))
        meta.update({'key': key,
                     'items': items,
                     'item': item})

        orig_callback = kwargs.get('callback', self.parse)

        def callback(response):
            self.log(response.status)
            if response.status is not 200:
                if 'dailyLimitExceeded' in response.body:
                    key = response.meta['key']
                    logging.error("dailyLimitExceeded for %s" % key)
                    # Do not retry key
                    if key in self._api_keys:
                        index = self._api_keys.index(key)
                        del(self._api_keys[index])
                    if not self._api_keys:
                        raise CloseSpider('dailyLimitExceeded and '
                                          'NO active keys')
                    meta = response.meta
                    if 'key' in meta:
                        del(meta['key'])
                    yield self._api_search(**meta)
                if 'accessNotConfigured' in response.body:
                    key = response.meta['key']
                    logging.error("accessNotConfigured for %s" % key)
                    # Do not retry key
                    if key in self._api_keys:
                        index = self._api_keys.index(key)
                        del(self._api_keys[index])
                    if not self._api_keys:
                        raise CloseSpider('accessNotConfigured and '
                                          'NO active keys')
                    meta = response.meta
                    if 'key' in meta:
                        del(meta['key'])
                    yield self._api_search(**meta)
                elif 'quotaExceeded' in response.body:
                    logging.error("quotaExceeded for %s" % response.meta['key'])
                    # Do not retry
                    raise CloseSpider('10 concurrent requests per profile in '
                                      'the Core Reporting API has been reached')
                elif 'invalidParameter' in response.body \
                        or 'badRequest' in response.body:
                    logging.error("invalidParameter or badRequest for %s" % response.meta['key'])
                    # Do not retry
                    raise CloseSpider('Invalid query or invalid parameter')
                elif 'backendError' in response.body:
                    logging.error("backendError for %s" % response.meta['key'])
                    # Do not retry this query more than once
                    if response.meta['item'] not in self._retry_items:
                        # Retry
                        self._retry_items.add(response.meta['item'])
                        yield self._api_search(**response.meta)
            # Valid response
            for p in orig_callback(response):
                yield p

            # Next item
            self._current_key_index += 1  # try next key
            key = self._get_key()
            response.meta.update({'key': key,
                                  'item': None})
            yield self._api_search(**response.meta)

        url = self._create_search_url(key, item)
        return Request(url, callback=callback, meta=meta, dont_filter=True)

# -*- coding: utf-8 -*-
import os
from os.path import join, exists
from time import time
import cPickle as pickle
import requests

from w3lib.http import headers_dict_to_raw, headers_raw_to_dict

from scrapy.http import Headers
from scrapy.responsetypes import responsetypes
from scrapy.http.response.html import HtmlResponse

def read_meta(rpath):
    metapath = join(rpath, 'pickled_meta')
    if not exists(metapath):
        return  # not found
    with open(metapath, 'rb') as f:
        return pickle.load(f)

def retrieve_response(rpath):
    """
    Return response if present in cache, or None otherwise
    """
    metadata = read_meta(rpath)
    if metadata is None:
        return  # not cached
    with open(join(rpath, 'response_body'), 'rb') as f:
        body = f.read()
    with open(join(rpath, 'response_headers'), 'rb') as f:
        rawheaders = f.read()
    url = metadata.get('response_url')
    status = metadata['status']
    headers = Headers(headers_raw_to_dict(rawheaders))
    respcls = responsetypes.from_args(headers=headers, url=url)
    response = respcls(url=url, headers=headers, status=status, body=body)
    return response

def store_response(rpath, request, response):
    """
    Store the given response in the cache
    """
    if not exists(rpath):
        os.makedirs(rpath)
    metadata = {
        'url': request.url,
        'method': request.method,
        'status': response.status,
        'response_url': response.url,
        'timestamp': time(),
    }
    with open(join(rpath, 'meta'), 'wb') as f:
        f.write(repr(metadata))
    with open(join(rpath, 'pickled_meta'), 'wb') as f:
        pickle.dump(metadata, f, protocol=2)
    with open(join(rpath, 'response_headers'), 'wb') as f:
        f.write(headers_dict_to_raw(response.headers))
    with open(join(rpath, 'response_body'), 'wb') as f:
        f.write(response.body)
    with open(join(rpath, 'request_headers'), 'wb') as f:
        f.write(headers_dict_to_raw(request.headers))
    with open(join(rpath, 'request_body'), 'wb') as f:
        f.write(request.body)


def download_response(url, method='GET', tries=5):
    r = requests.request(method, url)
    current_try = 1
    while r.status_code != 200 and current_try < tries:
        r = requests.request(method, url)
        current_try += 1
    url = r.url.encode('utf-8')
    headers = r.headers.items()
    respcls = responsetypes.from_args(headers=headers, url=url, body=r.content)
    response = respcls(url=url, headers=headers, status=r.status_code, body=r.content)
    return response
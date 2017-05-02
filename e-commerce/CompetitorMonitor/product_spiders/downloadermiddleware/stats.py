# -*- coding: utf-8 -*-
from urlparse import urlparse

from scrapy.exceptions import NotConfigured
from scrapy.utils.request import request_httprepr
from scrapy.utils.response import response_httprepr
#from scrapy.stats import stats
#from scrapy.conf import settings


def _get_domain_from_url(url):
    url = urlparse(url).netloc
    if url.startswith('www.'):
        url = url[4:]
    return url


class DownloaderStatsPerDomain(object):

    def __init__(self, crawler):
        self.settings = crawler.settings
        self.stats = crawler.stats
        #if not self.settings.get('DOWNLOADER_STATS'):
        #    raise NotConfigured

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def process_request(self, request, spider):
        domain = _get_domain_from_url(request.url)
        self.stats.inc_value('downloader/%s/request_count' % domain, spider=spider)
        self.stats.inc_value('downloader/%s/request_method_count/%s' % (domain, request.method), spider=spider)
        reqlen = len(request_httprepr(request))
        self.stats.inc_value('downloader/%s/request_bytes' % domain, reqlen, spider=spider)

    def process_response(self, request, response, spider):
        domain = _get_domain_from_url(response.url)
        self.stats.inc_value('downloader/%s/response_count' % domain, spider=spider)
        self.stats.inc_value('downloader/%s/response_status_count/%s' % (domain, response.status), spider=spider)
        reslen = len(response_httprepr(response))
        self.stats.inc_value('downloader/%s/response_bytes' % domain, reslen, spider=spider)
        return response


def get_request_proxy(request):
    return request.meta.get('proxy', None)


class DownloaderProxyStats(object):

    def __init__(self, crawler):
        self.settings = crawler.settings
        self.stats = crawler.stats
        #if not self.settings.get('DOWNLOADER_STATS'):
        #    raise NotConfigured

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def process_request(self, request, spider):
        proxy = get_request_proxy(request)
        if proxy:
            self.stats.inc_value('downloader/proxy/%s/request_count' % proxy, spider=spider)
            self.stats.inc_value('downloader/proxy/%s/request_method_count/%s' % (proxy, request.method), spider=spider)
            reqlen = len(request_httprepr(request))
            self.stats.inc_value('downloader/proxy/%s/request_bytes' % proxy, reqlen, spider=spider)

    def process_response(self, request, response, spider):
        proxy = get_request_proxy(request)
        if proxy:
            self.stats.inc_value('downloader/proxy/%s/response_count' % proxy, spider=spider)
            self.stats.inc_value('downloader/proxy/%s/response_status_count/%s' % (proxy, response.status), spider=spider)
            reslen = len(response_httprepr(response))
            self.stats.inc_value('downloader/proxy/%s/response_bytes' % proxy, reslen, spider=spider)
        return response


class DownloaderProxyStatsPerDomain(object):

    def __init__(self, crawler):
        self.settings = crawler.settings
        self.stats = crawler.stats
        #if not self.settings.get('DOWNLOADER_STATS'):
        #    raise NotConfigured

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def process_request(self, request, spider):
        proxy = get_request_proxy(request)
        if proxy:
            domain = _get_domain_from_url(request.url)
            self.stats.inc_value('downloader/proxy/%s/domain/%s/request_count' % (proxy, domain), spider=spider)
            self.stats.inc_value('downloader/proxy/%s/domain/%s/request_method_count/%s' % (proxy, domain, request.method), spider=spider)
            reqlen = len(request_httprepr(request))
            self.stats.inc_value('downloader/proxy/%s/domain/%s/request_bytes' % (proxy, domain), reqlen, spider=spider)

    def process_response(self, request, response, spider):
        proxy = get_request_proxy(request)
        if proxy:
            domain = _get_domain_from_url(response.url)
            self.stats.inc_value('downloader/proxy/%s/domain/%s/response_count' % (proxy, domain), spider=spider)
            self.stats.inc_value('downloader/proxy/%s/domain/%s/response_status_count/%s' % (proxy, domain, response.status), spider=spider)
            reslen = len(response_httprepr(response))
            self.stats.inc_value('downloader/proxy/%s/domain/%s/response_bytes' % (proxy, domain), reslen, spider=spider)
        return response

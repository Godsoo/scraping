# -*- coding: utf-8 -*-
"""
Base class for spiders, which use big site method.
More information here: https://www.assembla.com/spaces/competitormonitor/wiki/Creating_spiders_for_big_sites

Any fixes and improvements are welcomed, but be careful, as there are already many spider inheriting from it.
"""
import json
import csv
import os.path
import shutil
import time
import logging
from datetime import datetime

import inspect

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from decimal import Decimal

from scrapy import signals
from scrapy import Spider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.xlib.pydispatch import dispatcher
from scrapy import log

from product_spiders.items import Product, \
    ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import new_system_api_roots, api_key
from product_spiders.utils import read_json_lines_from_file_generator, get_crawl_meta_file


def get_class_module_root_path(cls):
    return os.path.abspath(os.path.dirname(inspect.getfile(cls)))

def is_weekday_today(weekday, dt=None):
    """
    Check if today is the week day, which is passed.
    0 - Monday
    1 - Tuesday
    ...
    6 - Sunday
    """
    if not dt:
        dt = datetime.now()
    return int(dt.weekday()) == int(weekday)

def _split_cron_range(cron_range):
    """
    >>> _split_cron_range("1,2")
    [1, 2]
    >>> _split_cron_range("1")
    [1]
    >>> _split_cron_range("1-4")
    [1, 2, 3, 4]
    >>> _split_cron_range("1-10,15,20")
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20]
    """
    res = []
    for part in cron_range.split(','):
        if '-' in part:
            start, end = part.split('-')
            res += range(int(start), int(end) + 1)
        else:
            res.append(int(part))
    return res

def _cron_dow_to_set(dow):
    if dow == '*':
        return set(range(0, 6 + 1))
    else:
        res = set()
        for part in _split_cron_range(dow):
            if part == 0:
                part = 6
            else:
                part -= 1
            res.add(part)
        return res

def _cron_dom_to_set(dom):
    if dom == '*':
        return set(range(0, 31 + 1))
    else:
        return set(_split_cron_range(dom))

def _cron_m_to_set(m):
    if m == '*':
        return set(range(0, 12 + 1))
    else:
        return set(_split_cron_range(m))

def is_cron_today(dom, m, dow, dt=None):
    """
    >>> date = datetime(2014, 10, 2)
    >>> is_cron_today("2", "*", "*", date)
    True
    >>> is_cron_today("2", "*", "4", date)
    True
    >>> is_cron_today("2", "*", "4,5", date)
    True
    >>> is_cron_today("2", "*", "3-5", date)
    True
    >>> is_cron_today("1-5,8", "*", "*", date)
    True
    >>> is_cron_today("2,8-15", "*", "*", date)
    True
    >>> is_cron_today("1,8-20", "*", "*", date)
    False
    >>> is_cron_today("2", "*", "3", date)
    False
    >>> is_cron_today("3", "*", "4", date)
    False
    >>> is_cron_today("*", "*", "4", date)
    True
    >>> is_cron_today("*", "2", "*", date)
    False
    >>> is_cron_today("*", "10", "*", date)
    True
    >>> is_cron_today("*", "2-9", "*", date)
    False
    >>> is_cron_today("*", "2-10", "*", date)
    True
    >>> is_cron_today("*", "9-11", "*", date)
    True
    """
    if not dt:
        dt = datetime.now()
    # transforming day-of-the-week from cron format to python format
    dow = _cron_dow_to_set(dow)
    dow_matches = dt.weekday() in dow

    dom = _cron_dom_to_set(dom)
    dom_matches = dt.day in dom

    m = _cron_m_to_set(m)
    m_matches = dt.month in m

    return dow_matches and dom_matches and m_matches


class SpiderRootPathMetaclass(type):
    """
    Helper to define 'root_path' at class creation time

    For BigSiteMethodSpider base class we need to set 'root_path' attribute at class creation time.
    So when some class inherits from BigSiteMethodSpider and another class inherits from that one, second child
    will have `root_path` to it's parent folder. Also, second child will be able to use first child's 'root_path'
    value at class creation time. Actually, any code importing module with child of BigSiteMethodSpider will be able
    to use child class's 'root_path' attribute.

    For this to work we define metaclass (class of class) for BigSiteMethodSpider. __init__ method does the work
    """
    def __init__(cls, name, bases, attrs):
        """
        The method is invoked on class creation time (when a class with metaclass BigSiteMethodSpiderInitializer
        is created first time, for example when its module is read by interpreter). Class already have all
        attributes and methods defined in it's body. The method checks if 'root_path' own attribute of class
        (not of its parents) already have value and if not - sets it to parent folder of class's module
        """
        # redefine 'root_path' if class has no own attribute named 'root_path'
        if 'root_path' not in cls.__dict__ or cls.__dict__['root_path'] is None:
            cls.root_path = get_class_module_root_path(cls)
        super(SpiderRootPathMetaclass, cls).__init__(name, bases, attrs)


class BigSiteMethodSpider(Spider):
    """
    Base class for spiders using 'big site method'.

    There are several instance value, which spider MUST have for this to work properly:
    'name' - this attribute is mandatory for all spiders, also it's used to save results of full run crawl
    'allowed_domains' - this attribute is also mandatory for all spiders, also 'competitormonitor.com' is automatically
        added to it on initialization
    'website_id' - this attribute is used to get matches from main app (or old app) on simple run
    <TO REMOVE> 'start_urls' - this attribute should contain list of urls to be processed by 'parse_full' method
    'parse' or 'parse_full' - this is the method to parse responses of 'start_urls' requests
    'parse_product' - this is the method to parse individual product pages

    'start_urls' and 'parse_full' actually mimics behaviour of base spider (it uses 'start_urls' and 'parse' method).
    Feel free to override '_start_requests_full' method to achieve more custom behavior (it mimics behavior of
    'start_requests' method for full run only)

    There are also instance variables which can customize behavior of spider. They will be described inline
    """
    root_path = None
    __metaclass__ = SpiderRootPathMetaclass
    # if set to False will never do full run and always take products list from file. Useful for spiders, which
    # can use results of other spider
    do_full_run = True
    # on which week day should full run be performed, to customize behaviour see 'full_run_required' method
    full_crawl_day = 0  # default Monday

    # full crawl day in cron format
    # disabled by default so old spiders with full_crawl_day can work OK
    # full_crawl_cron = "* * 1"
    full_crawl_cron = ""

    # set customer filename to get all products list, must be absolute path
    # by default it's constructed from 'root_path' and spider's name
    all_products_file = None
    all_products_file_bak = None
    # the same for metadata
    all_meta_file = None
    all_meta_file_format = "json"
    all_meta_file_bak = None

    # metadata class. Should be not None for all spiders with metadata
    metadata_class = None

    # matches source
    new_system = True
    old_system = False

    # retry on errors
    do_retry = False
    max_retry_count = 15
    retry_sleep = 60

    # customize product loader, can be useful if you want to use other then default product loader
    # see axemusic/bhphotovideo_spider.py for an example
    product_loader = ProductLoader

    # additional cookies to send, used in pedalpedal/evanscycles_com.py spider to set currency and delivery destination
    additional_cookies = None

    # following values should be non-empty in child-classes
    name = None
    allowed_domains = None
    website_id = None

    # competitor monitor server (can be secondary) to load matches from
    compmon_host = 'http://5.9.94.52:6543/'

    def __init__(self, *args, **kwargs):
        """
        Presets some instance variables and sets signal handler for 'spider closed' (which will save spider results
        on full run)
        Also checks if all necessary instance variables are defined
        """
        self.log("[BSM] Initializing BSM spider")
        super(BigSiteMethodSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.prods_count = 0
        self.matched = []
        self.matched_identifiers = set()
        self.errors = []

        self.log("Creating spider for big site method: %s" % str(self.__class__.__name__))

        # check all prerequisites: name, start_urls, website_id, parse_product, parse_full
        if not hasattr(self, 'name') or self.name is None:
            msg = "Big Site Method issue: spider has not attribute 'name'"
            self.log(msg, level=logging.ERROR)
            self.errors.append(msg)
        if not hasattr(self, 'website_id') or self.website_id is None:
            msg = "Big Site Method issue: spider has not attribute 'website_id'"
            self.log(msg, level=logging.ERROR)
            self.errors.append(msg)
        # if not hasattr(self, 'start_urls'):
        #     msg = "Big Site Method issue: spider has not attribute 'start_urls'"
        #     self.log(msg, level=logging.ERROR)
        #     self.errors.append(msg)
        # elif len(self.start_urls) < 1:
        #     msg = "Big Site Method issue: spider's start_urls list is empty"
        #     self.log(msg, level=logging.ERROR)
        #     self.errors.append(msg)
        if not hasattr(self, 'allowed_domains') or self.allowed_domains is None:
            msg = "Big Site Method issue: spider has not attribute 'allowed_domains'"
            self.log(msg, level=logging.ERROR)
            self.errors.append(msg)
        if not hasattr(self, 'parse_product') or not callable(self.parse_product):
            msg = "Big Site Method issue: spider has not method 'parse_product'"
            self.log(msg, level=logging.ERROR)
            self.errors.append(msg)
        if (not hasattr(self, 'parse_full') or not callable(self.parse_full)) and\
                (not hasattr(self, 'parse') or not callable(self.parse)):
            msg = "Big Site Method issue: spider has not method 'parse_full'"
            self.log(msg, level=logging.ERROR)
            self.errors.append(msg)

        self.log("Name: %s" % self.name)
        if hasattr(self, 'start_urls') and self.start_urls:
            self.log("Start url: %s" % self.start_urls[0])
        else:
            self.log("No start urls")
        self.log("Website id: %s" % self.website_id)
        self.log("Root path: %s" % self.root_path)
        self.log("Params: %s" % str(self.params) if hasattr(self, 'params') else '')

        self.full_run = False
        self.simple_run = False
        self.prev_crawl_processed = False

        self.cm_data = {}

    def _metadata_enabled(self):
        if hasattr(self, 'enable_metadata') and self.enable_metadata:
            return True
        else:
            return False

    def _get_crawl_local_filename(self):
        return self.name + '_products.csv'

    def _get_crawl_local_meta_filename(self):
        filename = self.name + '_products.json'
        filepath = os.path.join(self.root_path, filename)
        if os.path.exists(filepath):
            return filepath, 'json'
        filename = self.name + '_products.json-lines'
        filepath = os.path.join(self.root_path, filename)
        if os.path.exists(filepath):
            return filepath, 'json-lines'
        return None, None

    def _get_prev_crawl_file(self):
        if self.all_products_file:
            return self.all_products_file

        crawl_file = os.path.join(self.root_path, '%s_crawl' % self.name)
        if hasattr(self, 'prev_crawl_id'):
            return 'data/%s_products.csv' % self.prev_crawl_id
        elif os.path.exists(crawl_file):
            crawl_id = open(crawl_file).read().strip()
            return 'data/%s_products.csv' % crawl_id
        else:
            return os.path.join(self.root_path, self._get_crawl_local_filename())

    def _get_prev_crawl_meta_file(self):
        if self.all_meta_file and self.all_meta_file_format:
            return self.all_meta_file, self.all_meta_file_format

        crawl_file = os.path.join(self.root_path, '%s_crawl' % self.name)
        if hasattr(self, 'prev_crawl_id'):
            filename, file_format = get_crawl_meta_file(self.prev_crawl_id)
            return filename, file_format
        elif os.path.exists(crawl_file):
            crawl_id = open(crawl_file).read().strip()
            filename, file_format = get_crawl_meta_file(crawl_id)
            return filename, file_format
        else:
            return self._get_crawl_local_meta_filename()

    def _set_proper_domain(self):
        self.log("[BSM] Setting domain")
        if hasattr(self, 'upload_dst'):
            if self.upload_dst in new_system_api_roots:
                self.compmon_host = new_system_api_roots[self.upload_dst]

        if hasattr(self, 'allowed_domains') \
                and self.allowed_domains is not None:
            if 'competitormonitor.com' not in self.allowed_domains:
                if isinstance(self.allowed_domains, set):
                    self.allowed_domains.add('competitormonitor.com')
                elif isinstance(self.allowed_domains, tuple):
                    self.allowed_domains = self.allowed_domains + ('competitormonitor.com', )
                else:
                    self.allowed_domains.append('competitormonitor.com')
            compmon_host = self.compmon_host.split(":")[-2].replace('//', '')
            if compmon_host not in self.allowed_domains:
                if isinstance(self.allowed_domains, set):
                    self.allowed_domains.add(compmon_host)
                elif isinstance(self.allowed_domains, tuple):
                    self.allowed_domains = self.allowed_domains + (compmon_host, )
                else:
                    self.allowed_domains.append(compmon_host)
        if self.compmon_host.endswith('/'):
            self.compmon_host = self.compmon_host[:-1]
        self.log("[BSM] Compmon host: %s" % self.compmon_host)

    def start_requests(self):
        """
        Check if it's time for full run or simple run and invoke request accordingly.

        Please, do not override as it does some auxiliary actions, which are necessary for proper work of spider
        """
        self._set_proper_domain()
        if self.full_run_required():
            self.log('Full run')
            self.full_run = True
            all_products_file = self._get_prev_crawl_file()
            all_products_file_bak = all_products_file + '.bak'
            if os.path.exists(all_products_file):
                shutil.copy(all_products_file, all_products_file_bak)

            if self._metadata_enabled():
                all_meta_file, file_format = self._get_prev_crawl_meta_file()
                if all_meta_file and os.path.exists(all_meta_file):
                    all_meta_file_bak = all_meta_file + '.bak'
                    shutil.copy(all_meta_file, all_meta_file_bak)

            start_req = self._start_requests_full()
        else:
            self.log('Simple run')
            self.simple_run = True
            self.prev_crawl_processed = False

            start_req = self._start_requests_simple()

        for req in start_req:
            yield req

    def spider_idle(self, spider):
        """
        On simple run invokes first url from 'start_urls' with callback on 'parse_simple' method.
        It's not necessary to do request, can just get all products inside this method, but
        if the site is not available it will fail (which is a sign for maintenance).
        """
        self.log("[BSM] Spider idle")
        if spider.name == self.name:
            if self.simple_run and not self.prev_crawl_processed:
                if hasattr(self, 'start_urls') and self.start_urls:
                    url = self.start_urls[0]
                elif hasattr(self, 'domain') and self.domain:
                    url = "http://" + self.domain
                else:
                    url = "http://" + self.allowed_domains[0]

                request = Request(url, dont_filter=True, callback=self.closing_parse_simple,
                                  meta={'dont_redirect': True,
                                        'handle_httpstatus_all': True},)
                self.crawler.engine.crawl(request, self)

    def spider_closed(self, spider):
        """
        On full run saves crawl results for future use if it's full run then.
        """
        self.log("[BSM] Spider finished")
        if spider.name == self.name:
            if self.full_run:
                self.log("[BSM] Closed")
                # self.log("[BSM] Saving crawl id of full run")
                # all_products_file = self._get_prev_crawl_file()
                # shutil.copy('data/%s_products.csv' % spider.crawl_id, all_products_file)
                # with open(os.path.join(self.root_path, '%s_crawl' % spider.name), 'w') as f:
                #     f.write(str(spider.crawl_id))
                # if self._metadata_enabled():
                #     all_meta_file = self._get_prev_crawl_meta_file()
                #     shutil.copy('data/meta/%s_meta.json' % spider.crawl_id, all_meta_file)

    def _start_requests_full(self):
        """
        Invokes starting requests for full run. Feel free to overwrite if you need more custom behavior
        """
        if not hasattr(self, 'start_urls'):
            msg = "Big Site Method issue: spider has not attribute 'start_urls'"
            self.log(msg, level=logging.ERROR)
            self.errors.append(msg)
            return
        elif len(self.start_urls) < 1:
            msg = "Big Site Method issue: spider's start_urls list is empty"
            self.log(msg, level=logging.ERROR)
            self.errors.append(msg)
        for url in self.start_urls:
            if self.do_retry:
                errback = lambda failure, url = url, metadata = {}: \
                    self.bsm_retry_download(failure, url, metadata, self.parse_full)
            else:
                errback = None

            yield Request(
                url=url,
                callback=self.parse_full,
                errback=errback,
                cookies=self.additional_cookies,
                dont_filter=True)

    def _start_requests_simple(self):
        """
        Invokes starting requests for simple run. Invokes requests to get matches from apps

        Feel free to override for custom behavior
        """
        if self.new_system:
            yield self._get_matches_new_system_request()

        if self.old_system:
            yield self._get_matches_old_system_request()

    def _check_day_is_full_run(self):
        if hasattr(self, 'params') and 'full_crawl_cron' in self.params:
            full_crawl_cron = self.params['full_crawl_cron']
            self.log("[BSM] Full crawl cron from params. Cron: %s, params: %s" % (full_crawl_cron, str(self.params)))
        else:
            full_crawl_cron = self.full_crawl_cron
            self.log("[BSM] Full crawl cron from spider attr: %s" % full_crawl_cron)

        if full_crawl_cron:
            try:
                dom, m, dow = full_crawl_cron.split()
                res = is_cron_today(dom, m, dow)
                if res:
                    self.log("[BSM] Today is full run according to cron: %s, today: %s" %
                             (full_crawl_cron, datetime.now().strftime("%c")))
                return res
            except ValueError:
                self.log("[BSM] Failed to check cron: %s. Proceeding to check day (old method)" % full_crawl_cron)
                pass
        else:
            self.log("[BSM] No cron setup. Proceeding to check day (old method)")
        # old method
        if hasattr(self, 'params') and 'full_crawl_day' in self.params:
            full_crawl_day = self.params['full_crawl_day']
            self.log("[BSM] Full crawl day from params. Day: %s, params: %s" % (full_crawl_day, str(self.params)))
        else:
            full_crawl_day = self.full_crawl_day
            self.log("[BSM] Full crawl day from spider attr: %s" % full_crawl_day)

        res = is_weekday_today(full_crawl_day)
        if res:
            self.log("[BSM] Today is full run according to day: %s, today: %s" % (full_crawl_day,
                                                                                  datetime.now().strftime("%c")))
        return res

    def full_run_required(self):
        """
        Checks if spider needs full crawl

        Feel free to override for custom behavior
        """
        if not self.do_full_run:
            return False

        all_products_file = self._get_prev_crawl_file()
        if not os.path.exists(all_products_file):
            self.log("[BSM] Today is full run because prev crawl data file does not exists: %s" % all_products_file)
            return True

        if self._metadata_enabled():
            all_meta_file, file_format = self._get_prev_crawl_meta_file()
            if not os.path.exists(all_meta_file):
                self.log("[BSM] Today is full run because prev crawl metadata file does not exists: %s" % all_meta_file)
                return True

        if hasattr(self, 'params') and 'do_full_run_only_once' in self.params:
            last_crawl_date = None
            if hasattr(self, 'prev_crawl_date'):
                last_crawl_date = self.prev_crawl_date
            today_date = datetime.today().date()
            if self.params['do_full_run_only_once'] and last_crawl_date and last_crawl_date == today_date:
                return False

        return self._check_day_is_full_run()

    def _get_matches_new_system_request(self):
        """
        Constructs request which loads matches to new system
        """
        url = ('%(compmon_host)s/api/get_matched_products_count.json?'
               'website_id=%(website_id)s&api_key=%(api_key)s' %
               {
                   'compmon_host': self.compmon_host,
                   'website_id': self.website_id,
                   'api_key': api_key
               })
        self.log("Loading matches from new system: %s" % url)
        if self.do_retry:
            errback = lambda failure, url = url, metadata = {}: \
                self.bsm_retry_download(failure, url, metadata, self.parse_matches_count_new_system)
        else:
            errback = None
        return Request(
            url=url,
            callback=self.parse_matches_count_new_system,
            errback=errback,
            cookies=self.additional_cookies,
            dont_filter=True
        )

    def _get_matches_old_system_request(self):
        """
        Constructs request which loads matches to old system
        """
        url = ('http://www.competitormonitor.com/login.html?action=get_products_api&'
               'website_id=%(website_id)s&matched=1' % {'website_id': self.website_id})
        self.log("Loading matches from old system: %s" % url)
        if self.do_retry:
            errback = lambda failure, url = url, metadata = {}: \
                self.bsm_retry_download(failure, url, metadata, self.parse_matches_old_system)
        else:
            errback = None
        return Request(
            url=url,
            callback=self.parse_matches_old_system,
            errback=errback,
            cookies=self.additional_cookies
        )

    def parse(self, response):
        raise NotImplementedError("Spider must implement `parse` or `parse_full`")

    def parse_full(self, response):
        gen = self.parse(response)
        if gen:
            for r in gen:
                yield r
        else:
            msg = "[BSM] `parse` method does not return generator or iterable"
            self.errors.append(msg)
            self.log(msg, level=log.ERROR)

    def parse_matches_count_new_system(self, response):
        try:
            res = json.loads(response.body)
        except ValueError:
            self.log("Website is invalid in web app: %s" % self.website_id, level=log.ERROR)
            return

        self.cm_data['count'] = res['count']

        url = ('%(compmon_host)s/api/get_matched_products_paged.json?'
               'website_id=%(website_id)s&api_key=%(api_key)s&start=0&count=1000' %
               {
                   'compmon_host': self.compmon_host,
                   'website_id': self.website_id,
                   'api_key': api_key
               })
        self.log("Loading matches from new system: %s" % url)
        if self.do_retry:
            errback = lambda failure, url = url, metadata = {}: \
                self.bsm_retry_download(failure, url, metadata, self.parse_matches_paged_new_system)
        else:
            errback = None
        yield Request(
            url=url,
            callback=self.parse_matches_paged_new_system,
            errback=errback,
            cookies=self.additional_cookies,
            dont_filter=True,
            meta={
                'start': 0,
                'count': 1000
            }
        )

    def parse_matches_paged_new_system(self, response):
        """
        Processes matches from new system.
        Invokes product urls requests with callback to 'parse_product
        """
        try:
            products = json.loads(response.body)
        except ValueError:
            self.log("Website is invalid in web app: %s" % self.website_id, level=log.ERROR)
            return

        cur_offset = response.meta['start']
        cur_count = response.meta['count']

        matches = products.get('matches', [])
        if not matches and cur_offset == 0 and self.cm_data['count'] > 0:
            self.errors.append('Big Site Method issue: matches not found')
        self.matched += matches
        self.matched_identifiers = self.matched_identifiers.union([x['identifier'] for x in self.matched])
        self.log("Loaded %d matches from new system" % len(products.get('matches', [])))

        for prod in self.matched:
            url = prod['url']
            if not url:
                continue

            if self.do_retry:
                errback = lambda failure, url = url, metadata = {}: \
                    self.bsm_retry_download(failure, url, metadata, self.parse_product)
            else:
                errback = None

            meta = {
                'item': prod
            }

            # patch for old base amazon spider
            prod_obj = Product()
            for field, value in prod.items():
                if field in prod_obj.fields:
                    prod_obj[field] = value
            meta['_product'] = prod_obj
            meta['check_price'] = True

            yield Request(
                url=url,
                callback=self.parse_product,
                errback=errback,
                cookies=self.additional_cookies,
                meta=meta
            )

        if cur_offset > self.cm_data['count']:
            return

        url = ('%(compmon_host)s/api/get_matched_products_paged.json?'
               'website_id=%(website_id)s&api_key=%(api_key)s&start=%(start)s&count=%(count)s' %
               {
                   'compmon_host': self.compmon_host,
                   'website_id': self.website_id,
                   'start': cur_offset + cur_count,
                   'count': cur_count,
                   'api_key': api_key
               })
        self.log("Loading matches from new system: %s" % url)
        if self.do_retry:
            errback = lambda failure, url = url, metadata = {}: \
                self.bsm_retry_download(failure, url, metadata, self.parse_matches_paged_new_system)
        else:
            errback = None
        yield Request(
            url=url,
            callback=self.parse_matches_paged_new_system,
            errback=errback,
            cookies=self.additional_cookies,
            dont_filter=True,
            meta={
                'start': cur_offset + cur_count,
                'count': cur_count
            }
        )

    def parse_matches_new_system(self, response):
        """
        Processes matches from new system.
        Invokes product urls requests with callback to 'parse_product
        """
        try:
            products = json.loads(response.body)
        except ValueError:
            self.log("Website is invalid in web app: %s" % self.website_id, level=log.ERROR)
            return
        matches = products.get('matches', [])
        if not matches:
            self.errors.append('Big Site Method issue: matches not found')
        self.matched += matches
        self.matched_identifiers = self.matched_identifiers.union([x['identifier'] for x in self.matched])
        self.log("Loaded %d matches from new system" % len(products.get('matches', [])))

        for prod in self.matched:
            url = prod['url']
            if not url:
                continue
            if self.do_retry:
                errback = lambda failure, url = url, metadata = {}: \
                    self.bsm_retry_download(failure, url, metadata, self.parse_product)
            else:
                errback = None

            meta = {
                'item': prod
            }

            # patch for old base amazon spider
            prod_obj = Product()
            for field, value in prod.items():
                if field in prod_obj.fields:
                    prod_obj[field] = value
            meta['_product'] = prod_obj
            meta['check_price'] = True

            yield Request(
                url=url,
                callback=self.parse_product,
                errback=errback,
                cookies=self.additional_cookies,
                meta=meta
            )

    def parse_matches_old_system(self, response):
        """
        Processes matches from old system.
        Invokes product urls requests with callback to 'parse_product
        """
        f = StringIO(response.body)
        reader = csv.DictReader(f)

        counter = 0
        for row in reader:
            self.matched_identifiers.add(row.get('identifier', row.get('name')))
            self.matched.append(row)
            counter += 1
        self.log("Loaded %d matches from old system" % counter)

        for product in self.matched:
            url = product['url']
            if not url:
                continue
            if self.do_retry:
                errback = lambda failure, url = url, metadata = {}: \
                    self.bsm_retry_download(failure, url, metadata, self.parse_product)
            else:
                errback = None
            yield Request(
                url=url,
                callback=self.parse_product,
                errback=errback,
                cookies=self.additional_cookies,
                meta={'item': product}
            )

    def closing_parse_simple(self, response):
        """
        Scrapes products from previous full run crawl results saved to file
        """
        self.prev_crawl_processed = True
        hxs = HtmlXPathSelector()
        self.log("[BSM] Processing prev crawl results")

        all_products_file = self._get_prev_crawl_file()
        all_products_file_bak = all_products_file + '.bak'

        self.log("Products file: %s" % all_products_file)
        self.log("Products file bak: %s" % all_products_file_bak)
        if not os.path.exists(all_products_file):
            msg = "Big Site Method issue: File with products list (%s) does not exists" % all_products_file
            self.log(msg, level=logging.ERROR)
            self.errors.append(msg)
            return

        if self._has_prev_metadata() and self._prev_meta_is_gen():
            all_meta_file, file_format = self._get_prev_crawl_meta_file()
            all_meta_file_bak = all_meta_file + '.bak'
            self.log("Meta file: %s" % all_meta_file)
            self.log("Meta file bak: %s" % all_meta_file_bak)

            # load products to memory in 1000s, so overall memory usage is not too big
            index = 0
            count = 1000
            products = self._load_some_products_from_file(all_products_file, index, count)
            while products:
                gen = read_json_lines_from_file_generator(all_meta_file)
                for meta in gen:
                    collect = meta['identifier'] not in self.matched_identifiers
                    if meta['identifier'] in products:
                        row = products[meta['identifier']]
                        product = self._create_product_from_raw_data(hxs, row)
                        product['metadata'] = self._create_metadata_from_raw_meta(meta['metadata'])
                        if collect:
                            yield product
                        del(products[meta['identifier']])
                if products:
                    for row in products.values():
                        collect = row['identifier'] not in self.matched_identifiers
                        if collect:
                            product = self._create_product_from_raw_data(hxs, row)
                            yield product
                index += count
                products = self._load_some_products_from_file(all_products_file, index, count)
        else:
            all_meta = self._get_meta()
            with open(all_products_file) as f:
                iter_products = csv.DictReader(f)
                for row in iter_products:
                    collect = True
                    if row['identifier']:
                        if row['identifier'] in self.matched_identifiers:
                            collect = False
                    else:
                        if row['name'] in self.matched_identifiers:
                            collect = False
                    if collect:
                        metadata = None
                        if row['identifier'] in all_meta:
                            raw_metadata = all_meta[row['identifier']]
                            metadata = self._create_metadata_from_raw_meta(raw_metadata)

                        product = self._create_product_from_raw_data(hxs, row)
                        if metadata is not None:
                            product['metadata'] = metadata

                        yield product

    def _create_product_from_raw_data(self, hxs, row):
        loader = self.product_loader(selector=hxs, item=Product())
        loader.add_value('url', row['url'])
        loader.add_value('sku', row.get('sku').decode('utf-8') if isinstance(row.get('sku'), str) else row.get('sku'))
        loader.add_value('identifier',
                         row['identifier'].decode('utf-8') if isinstance(row['identifier'], str) else row['identifier'])
        loader.add_value('name', row['name'].decode('utf-8') if isinstance(row['name'], str) else row['name'])
        loader.add_value('price', row['price'])
        loader.add_value('image_url', row['image_url'])
        loader.add_value('category',
                         row.get('category').decode('utf-8') if isinstance(row.get('category'), str) else row.get(
                             'category'))
        loader.add_value('brand',
                         row.get('brand').decode('utf-8') if isinstance(row.get('brand'), str) else row.get('brand'))

        if Decimal(row.get('shipping_cost') or 0):
            loader.add_value('shipping_cost', row.get('shipping_cost'))
        loader.add_value('stock', int(row['stock']) if row.get('stock') else None)
        loader.add_value('dealer',
                         row.get('dealer').decode('utf-8') if isinstance(row.get('dealer'), str) else row.get('dealer'))
        product = loader.load_item()
        return product

    def _create_metadata_from_raw_meta(self, raw_metadata):
        if self.metadata_class is not None:
            metadata = self.metadata_class()
            for field, value in raw_metadata.items():
                metadata[field] = value
        else:
            metadata = raw_metadata
        return metadata

    def bsm_retry_download(self, failure, url, metadata, callback):
        """
        Function to retry request if it failed.

        Retries only on allowed for retry HTTP codes.

        Number of maximum retries customizable by 'max_retry_count' instance variable of spider.
        Time to sleep between retries customizable by 'retry_sleep' instance variable of spider
        """
        status = failure.value.response.status
        # only retry on allowed HTTP codes
        if status not in self.settings['RETRY_HTTP_CODES']:
            return
        no_try = metadata.get('try', 1)
        self.log("[BSM] Try %d. Retrying to download %s" %
                 (no_try, url))
        if no_try < self.max_retry_count:
            metadata['try'] = no_try + 1
            time.sleep(self.retry_sleep)
            return Request(
                url=url,
                callback=callback,
                meta=metadata,
                dont_filter=True,
                errback=lambda failure, url=url, metadata=metadata:
                    self.bsm_retry_download(failure, url, metadata, callback),
                cookies=self.additional_cookies
            )

    def _get_meta(self):
        all_meta = {}
        if self._metadata_enabled():
            all_meta_file, file_format = self._get_prev_crawl_meta_file()
            if not all_meta_file:
                return {}
            all_meta_file_bak = all_meta_file + '.bak'
            self.log("Meta file: %s" % all_meta_file)
            self.log("Meta file bak: %s" % all_meta_file_bak)

            if file_format == 'json':
                with open(all_meta_file) as f:
                    data = f.read()
                    if len(data) < 1:
                        return
                    for meta in json.loads(data):
                        all_meta[meta['identifier']] = meta['metadata']
            elif file_format == 'json-lines':
                for meta in read_json_lines_from_file_generator(all_meta_file):
                    all_meta[meta['identifier']] = meta['metadata']
            else:
                raise ValueError("Unknown format for meta file: %s" % file_format)
        return all_meta

    def _has_prev_metadata(self):
        enabled = self._metadata_enabled()
        all_meta_file, file_format = self._get_prev_crawl_meta_file()
        return enabled and bool(all_meta_file) and os.path.exists(all_meta_file)

    def _load_some_products_from_file(self, all_products_file, index, count):
        res = {}
        with open(all_products_file) as f:
            for i, row in enumerate(csv.DictReader(f)):
                if len(res) > count:
                    break
                if i >= index:
                    res[row['identifier']] = row
        return res

    def _prev_meta_is_gen(self):
        all_meta_file, file_format = self._get_prev_crawl_meta_file()
        return file_format == 'json-lines'

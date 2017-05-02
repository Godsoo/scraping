import random
import sys
import os
import base64

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.contrib.downloadermiddleware.retry import RetryMiddleware

from urlparse import urljoin, urlparse
from itertools import cycle

import requests
from requests.auth import HTTPBasicAuth

HERE = os.path.dirname(os.path.abspath(__file__))

sys.path.append(os.path.abspath(os.path.join(HERE, '../productspidersweb')))

from product_spiders.utils import extract_auth_from_url, get_etc_hosts_rules
from productspidersweb.models import Spider, ProxyList
from db import Session

from product_spiders.contrib.proxyservice import ProxyServiceAPI

from config import (
    PROXY_SERVICE_HOST,
    PROXY_SERVICE_USER,
    PROXY_SERVICE_PSWD,
    PROXY_SERVICE_ALGORITHM_CHOICES,
    TOR_PROXY,
)

from twisted.internet.error import (
    TimeoutError as ServerTimeoutError,
    ConnectionRefusedError, ConnectionDone, ConnectError,
    ConnectionLost, TCPTimedOutError,
)
from twisted.internet.defer import TimeoutError as UserTimeoutError
from scrapy.core.downloader.handlers.http11 import TunnelError


PROXIES = ['http://108.62.195.141:3128', 'http://108.62.195.97:3128', 'http://108.62.195.253:3128',
           'http://108.62.195.18:3128', 'http://108.62.195.73:3128', 'http://108.62.195.108:3128',
           'http://23.19.188.246:3128', 'http://23.19.188.247:3128', 'http://23.19.188.248:3128',
           'http://23.19.188.249:3128', 'http://23.19.188.250:3128']


class ProxyMiddleWare(object):
    def __init__(self):
        dispatcher.connect(self.spider_opened,
                           signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed,
                           signal=signals.spider_closed)

        self.use_proxies = set()
        db_session = Session()
        self.proxy_lists = {}
        self.proxy_list_names = {}
        pl = db_session.query(ProxyList).all()
        for p in pl:
            self.proxy_lists[p.id] = p.proxies.split('\n')
            self.proxy_list_names[p.id] = p.name

        db_session.close()

    def _get_proxies(self, spider):
        if not getattr(spider, 'proxy_list_id'):
            return PROXIES
        else:
            return self.proxy_lists[spider.proxy_list_id]

    def _get_proxy_list_name(self, spider):
        if not getattr(spider, 'proxy_list_id'):
            return "Default"
        else:
            return self.proxy_list_names[spider.proxy_list_id]

    def spider_opened(self, spider):
        db_session = Session()
        db_spider = db_session.query(Spider).filter(Spider.name == spider.name).one()
        if db_spider and db_spider.use_proxies and not db_spider.use_tor:
            spider.proxy_list_id = db_spider.proxy_list_id
            self.use_proxies.add(spider.name)
            # for stats or PhantomJS
            spider._proxies_list = self._get_proxies(spider)
        db_session.close()

        self._etc_hosts_rules, self._etc_hosts_ips = get_etc_hosts_rules()

    def spider_closed(self, spider):
        if spider.name in self.use_proxies:
            self.use_proxies.remove(spider.name)

    def process_request(self, request, spider):
        if spider.name in self.use_proxies and not request.meta.get('keep_proxy_', False):
            proxy_name = self._get_proxy_list_name(spider)
            proxy_url = random.choice(self._get_proxies(spider))
            # extract user and password from url
            user, password, new_url = extract_auth_from_url(proxy_url)
            request.meta['proxy'] = new_url
            # add HTTP authorisation
            if user:
                request.headers['Proxy-Authorization'] = 'Basic ' + base64.encodestring("%s:%s" % (user, password))
            spider.log('Processing request to %s using proxy %s (%s)' % (request.url, request.meta['proxy'], proxy_name))

            return_request = False

            # The domain appears in /etc/hosts?
            urlp = urlparse(request.url)
            domain = urlp.netloc
            if domain in self._etc_hosts_rules:
                use_ip = self._etc_hosts_rules[domain]
                request = request.replace(url=request.url.replace(domain, use_ip))
                request.headers['Host'] = domain
                if not hasattr(spider, 'allowed_domains'):
                    spider.allowed_domains = []
                if use_ip not in spider.allowed_domains:
                    spider.allowed_domains.append(use_ip)
                return_request = True

            # Only HTTP for ProxyServer
            if proxy_name == 'ProxyServer' and request.url.startswith('https://'):
                request = request.replace(url=request.url.replace('https://', 'http://'))
                return_request = True

            if return_request:
                return request

    def process_response(self, request, response, spider):
        if spider.name in self.use_proxies and not request.meta.get('keep_proxy_', False):
            # The domain appears in /etc/hosts?
            urlp = urlparse(request.url)
            domain = urlp.netloc
            if domain in self._etc_hosts_ips:
                use_host = self._etc_hosts_ips[domain]
                return response.replace(url=response.url.replace(domain, use_host))
        return response

class ProxyServiceMiddleware(object):
    def __init__(self):
        dispatcher.connect(self.spider_opened,
                           signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed,
                           signal=signals.spider_closed)

        self.use_proxies = set()
        self.proxy_list = {}
        self.blocked_http_codes = [503, 403, 504]
        self.blocked_exceptions = (
            ServerTimeoutError, UserTimeoutError,
            ConnectionRefusedError, ConnectionDone, ConnectError,
            ConnectionLost, TCPTimedOutError, IOError, TunnelError)

        self._etc_hosts_rules, self._etc_hosts_ips = get_etc_hosts_rules()

    def _next_proxy(self, spider, try_load=True):
        try:
            if not spider.proxy_service_algorithm or spider.proxy_service_algorithm == 'random':
                next_proxy = random.choice(self.proxy_list[spider.proxy_service_target_id])
            else:
                next_proxy = self.proxy_list[spider.proxy_service_target_id].next()
        except:
            if try_load:
                self._load_proxy_list(spider)
                return self._next_proxy(spider, try_load=False)
            else:
                return None, None
        return next_proxy['id'], next_proxy['url']


    def _load_proxy_list(self, spider, blocked=None):
        target_id = spider.proxy_service_target_id
        if (target_id not in self.proxy_list) or (blocked is not None) or (target_id in self.proxy_list and not self.proxy_list[target_id]):
            proxy_service_api = ProxyServiceAPI(host=PROXY_SERVICE_HOST, user=PROXY_SERVICE_USER, password=PROXY_SERVICE_PSWD)
            length = getattr(spider, 'proxy_service_length', 10) or 10
            profile = getattr(spider, 'proxy_service_profile', None)
            locations = getattr(spider, 'proxy_service_locations', '')
            types = getattr(spider, 'proxy_service_types', '')
            ignore_ips = getattr(spider, 'proxy_service_ignore', '')  # <regex1>|<regex2>|...|<regexN>
            proxy_list = proxy_service_api.get_proxy_list(
                target_id, length=length, profile=profile,
                locations=locations, types=types, blocked=blocked, ignore_ips=ignore_ips,
                log=spider.log)

            if not spider.proxy_service_algorithm or spider.proxy_service_algorithm == 'random':
                self.proxy_list[target_id] = list(proxy_list)
            else:
                self.proxy_list[target_id] = cycle(proxy_list)

    def _target_exists(self, target_id):
        url = urljoin(PROXY_SERVICE_HOST, 'targets/%s')
        url = url % str(target_id)
        r = requests.get(url, auth=HTTPBasicAuth(PROXY_SERVICE_USER, PROXY_SERVICE_PSWD))
        return r.status_code == 200

    def _is_blocked_response(self, response, spider):
        if response.status in self.blocked_http_codes:
            return True
        elif hasattr(spider, 'proxy_service_check_response') and callable(spider.proxy_service_check_response):
            return spider.proxy_service_check_response(response)
        return False

    def _replace_proxy(self, request, spider):
        proxy_id, proxy_url = self._next_proxy(spider)
        if not proxy_id and not proxy_url:
            spider.log('>>> PROXY SERVICE ERROR: "next proxy not found"')
        else:
            # extract user and password from url
            user, password, new_url = extract_auth_from_url(proxy_url)
            request.meta['proxy'] = new_url
            request.meta['proxy_id'] = proxy_id
            # add HTTP authorization
            if user:
                request.headers['Proxy-Authorization'] = 'Basic ' + base64.encodestring("%s:%s" % (user, password))
            spider.log('Processing request to %s using proxy %s' % (request.url, request.meta['proxy']))

    def spider_opened(self, spider):
        db_session = Session()
        db_spider = db_session.query(Spider).filter(Spider.name == spider.name).one()
        if db_spider and db_spider.proxy_service_enabled and db_spider.proxy_service_target and not db_spider.use_proxies and not db_spider.use_tor:
            if self._target_exists(db_spider.proxy_service_target):
                self.use_proxies.add(spider.name)
                spider.proxy_service_target_id = db_spider.proxy_service_target
                spider.proxy_service_profile = db_spider.proxy_service_profile
                spider.proxy_service_types = db_spider.proxy_service_types
                spider.proxy_service_locations = db_spider.proxy_service_locations
                spider.proxy_service_length = db_spider.proxy_service_length
                spider.proxy_service_algorithm = 0
                if db_spider.proxy_service_algorithm:
                    for alg_id, alg in PROXY_SERVICE_ALGORITHM_CHOICES:
                        if db_spider.proxy_service_algorithm == alg_id:
                            spider.proxy_service_algorithm = alg
                            break
                self._load_proxy_list(spider)
            else:
                spider.log('>>> PROXY SERVICE ERROR: Target with id %s does not exist' % str(spider.proxy_service_target_id))
        db_session.close()

    def spider_closed(self, spider):
        if spider.name in self.use_proxies:
            self.use_proxies.remove(spider.name)

    def process_request(self, request, spider):
        disabled = 'proxy_service_disabled' in request.meta and request.meta['proxy_service_disabled']
        if spider.name in self.use_proxies and not disabled:
            self._replace_proxy(request, spider)

            # The domain appears in /etc/hosts?
            urlp = urlparse(request.url)
            domain = urlp.netloc
            if domain in self._etc_hosts_rules:
                use_ip = self._etc_hosts_rules[domain]
                request = request.replace(url=request.url.replace(domain, use_ip))
                request.headers['Host'] = domain
                if not hasattr(spider, 'allowed_domains'):
                    spider.allowed_domains = []
                if use_ip not in spider.allowed_domains:
                    spider.allowed_domains.append(use_ip)
                return request

    def process_response(self, request, response, spider):
        disabled = 'proxy_service_disabled' in request.meta and request.meta['proxy_service_disabled']
        if spider.name in self.use_proxies and not disabled:
            if self._is_blocked_response(response, spider) and 'proxy_id' in request.meta:
                self._load_proxy_list(spider, blocked=[int(request.meta['proxy_id'])])
            # The domain appears in /etc/hosts?
            urlp = urlparse(request.url)
            domain = urlp.netloc
            if domain in self._etc_hosts_ips:
                use_host = self._etc_hosts_ips[domain]
                return response.replace(url=response.url.replace(domain, use_host))
        return response

    def process_exception(self, request, exception, spider):
        if spider.name in self.use_proxies:
            if isinstance(exception, self.blocked_exceptions) and 'proxy_id' in request.meta:
                self._load_proxy_list(spider, blocked=[int(request.meta['proxy_id'])])
                self._replace_proxy(request, spider)

class TorMiddleWare(object):
    def __init__(self):
        dispatcher.connect(self.spider_opened,
                           signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed,
                           signal=signals.spider_closed)

        self.use_tor = set()

        self._etc_hosts_rules, self._etc_hosts_ips = get_etc_hosts_rules()

    def spider_opened(self, spider):
        db_session = Session()
        db_spider = db_session.query(Spider).filter(Spider.name == spider.name).one()
        if db_spider and db_spider.use_tor:
            self.use_tor.add(spider.name)
            # for stats or PhantomJS
            spider._proxies_list = [TOR_PROXY]
        db_session.close()

    def spider_closed(self, spider):
        if spider.name in self.use_tor:
            self.use_tor.remove(spider.name)

    def process_request(self, request, spider):
        if spider.name in self.use_tor:
            request.meta['proxy'] = TOR_PROXY
            spider.log('Processing request to %s using Tor' % (request.url,))

            # The domain appears in /etc/hosts?
            urlp = urlparse(request.url)
            domain = urlp.netloc
            if domain in self._etc_hosts_rules:
                use_ip = self._etc_hosts_rules[domain]
                request = request.replace(url=request.url.replace(domain, use_ip))
                request.headers['Host'] = domain
                if not hasattr(spider, 'allowed_domains'):
                    spider.allowed_domains = []
                if use_ip not in spider.allowed_domains:
                    spider.allowed_domains.append(use_ip)
                return request

    def process_response(self, request, response, spider):
        if spider.name in self.use_tor:
            # The domain appears in /etc/hosts?
            urlp = urlparse(request.url)
            domain = urlp.netloc
            if domain in self._etc_hosts_ips:
                use_host = self._etc_hosts_ips[domain]
                return response.replace(url=response.url.replace(domain, use_host))
        return response


class UserAgentMiddleWare(object):
    def __init__(self):
        dispatcher.connect(self.spider_opened,
                           signal=signals.spider_opened)
        self.agent_data = {}
        self.user_agents = []
        with open(os.path.join(HERE, 'useragents.txt')) as f:
            for l in f.read().split('\n'):
                if l:
                    self.user_agents.append(l)

    def spider_opened(self, spider):
        if getattr(spider, 'rotate_agent', None):
            self.agent_data[spider.name] = {'current': 0, 'processed': 0}

    def process_request(self, request, spider):
        if getattr(spider, 'rotate_agent', None):
            data = self.agent_data[spider.name]
            current = data['current']
            processed = data['processed']
            if processed >= 50 or request.meta.get('renew_user-agent', False):
                if current + 1 < len(self.user_agents):
                    current += 1
                else:
                    current = 0

                processed = 0

            request.headers['User-Agent'] = self.user_agents[current]
            processed += 1
            self.agent_data[spider.name] = {'current': current, 'processed': processed}
            spider.log('URL: %s. User-Agent: %s' % (request.url, self.user_agents[current]))

def get_spider_host(spider, db_session):
    from productspidersweb.models import WorkerServer
    worker_server = None
    if spider.worker_server_id:
        worker_server = db_session.query(WorkerServer).get(spider.worker_server_id)

    if not worker_server or worker_server.name == 'Default':
        return 'localhost'
    else:
        return worker_server.host

def send_command_renew_tor_ip(proxy_str, log=None):
    spider_system_ip = '148.251.79.44'
    url = 'http://%s/productspiders/renew_tor_ip.json' % spider_system_ip
    data = {'proxy': proxy_str}

    r = requests.post(url, data=data)
    if r.json()['status'] == 'ok':
        if log:
            log("[TorRetryMiddleware]: Tor renewed")
    else:
        if log:
            log("[TorRetryMiddleware]: Failed to renew tor: %s" % r.json().get('msg'))

    return

class TorRenewMiddleware(object):
    def __init__(self):
        dispatcher.connect(self.spider_opened,
                           signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed,
                           signal=signals.spider_closed)

        self.blocked_http_codes = [503, 403]
        self.blocked_exceptions = (ServerTimeoutError, UserTimeoutError, TCPTimedOutError, IOError)

        self.tor_renew_ip = set()

    def spider_opened(self, spider):
        db_session = Session()
        db_spider = db_session.query(Spider).filter(Spider.name == spider.name).one()
        if db_spider and db_spider.use_proxies or db_spider.use_tor:
            self.tor_renew_ip.add(spider.name)
        db_session.close()

    def spider_closed(self, spider):
        if spider.name in self.tor_renew_ip:
            self.tor_renew_ip.remove(spider.name)

    def _is_blocked_response(self, response, spider):
        if response.status in self.blocked_http_codes:
            spider.log("[TorRenewMiddleware] Response status code in list of blocked codes: %s in %s" %
                         (response.status, str(self.blocked_http_codes)))
            return True
        elif hasattr(spider, 'is_response_blocked') and callable(spider.is_response_blocked):
            return spider.is_response_blocked(response)
        elif hasattr(spider, 'proxy_service_check_response') and callable(spider.proxy_service_check_response):
            return spider.proxy_service_check_response(response)
        return False

    def _tor_renew(self, spider):
        if spider.name in self.tor_renew_ip:
            if hasattr(spider, '_proxies_list'):
                spider.log("[TorRenewMiddleware] Renewing Tor")
                for proxy_str in spider._proxies_list:
                    # send command to renew IP for proxy
                    send_command_renew_tor_ip(proxy_str, spider.log)

    def process_request(self, request, spider):
        if request.meta.get('renew_tor', False):
            self._tor_renew(spider)

    def process_response(self, request, response, spider):
        if self._is_blocked_response(response, spider):
            self._tor_renew(spider)
        return response

    def process_exception(self, request, exception, spider):
        if isinstance(exception, self.blocked_exceptions):
            self._tor_renew(spider)

class TorRetryMiddleware(RetryMiddleware):
    def __init__(self, *args, **kwargs):
        super(TorRetryMiddleware, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_opened,
                           signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed,
                           signal=signals.spider_closed)

        self.tor_renew_ip = set()

    def spider_opened(self, spider):
        db_session = Session()
        db_spider = db_session.query(Spider).filter(Spider.name == spider.name).one()
        tor_renew = (db_spider and getattr(db_spider, 'tor_renew_on_retry', False)) or \
                    (getattr(spider, '_tor_retry_renew', False))
        if tor_renew:
            self.tor_renew_ip.add(spider.name)
            # for stats or PhantomJS
            spider._tor_retry_renew = True
        db_session.close()

    def spider_closed(self, spider):
        if spider.name in self.tor_renew_ip:
            self.tor_renew_ip.remove(spider.name)

    def _tor_renew(self, spider):
        if spider.name in self.tor_renew_ip:
            if hasattr(spider, '_proxies_list'):
                spider.log("[TorRetryMiddleware] Renewing Tor")
                for proxy_str in spider._proxies_list:
                    # send command to renew IP for proxy
                    send_command_renew_tor_ip(proxy_str, spider.log)

    def _tor_restart(self, spider):
        if hasattr(spider, 'restart_tor'):
            spider.restart_tor()

    def _retry(self, request, reason, spider):
        self._tor_renew(spider)
        self._tor_restart(spider)

        return super(TorRetryMiddleware, self)._retry(request, reason, spider)


class AmazonMiddleWare(object):
    SESSIONS = 10
    current_session = 0
    def process_request(self, request, spider):
        if not hasattr(spider, 'use_amazon_middleware') or not spider.use_amazon_middleware:
            return

        if not request.meta.get('keep_session'):
            self.current_session = (self.current_session + 1) % self.SESSIONS
            spider.log('Session is {}'.format(self.current_session))
            request.meta['cookiejar'] = self.current_session
            #request.meta['proxy'] = 'http://' + self.PROXIES[self.current_session]
        else:
            spider.log('Keeping session')
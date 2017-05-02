# -*- coding: utf-8 -*-

import time

from w3lib.url import urljoin_rfc, add_or_replace_parameter
import requests
from requests.auth import HTTPBasicAuth


class ProxyServiceAPI(object):

    def __init__(self, host, user, password, retry=True, max_retry_no=10):
        self.host = host
        self.user = user
        self.password = password

        self.retry = retry
        self.max_retry = max_retry_no

    def get_proxy_list(self, target_id, length=10, profile=None, locations='', types='', ignore_ips='', blocked=None, log=None):
        proxy_list = []

        proxy_list_url = urljoin_rfc(self.host, 'proxy_list')
        proxy_list_url = add_or_replace_parameter(proxy_list_url, 'target_id', str(target_id))
        proxy_list_url = add_or_replace_parameter(proxy_list_url, 'length', str(length))
        if profile and isinstance(profile, int):
            proxy_list_url = add_or_replace_parameter(proxy_list_url, 'profile', str(profile))
        else:
            if locations:
                proxy_list_url = add_or_replace_parameter(proxy_list_url, 'locations', str(locations))
            if types:
                proxy_list_url = add_or_replace_parameter(proxy_list_url, 'types', str(types))
        if ignore_ips:
            proxy_list_url = add_or_replace_parameter(proxy_list_url, 'ignore', ignore_ips)
        if blocked and isinstance(blocked, list):
            proxy_list_url = add_or_replace_parameter(proxy_list_url, 'blocked', '|'.join(map(str, blocked)))

        try_no = 1
        try_query = True
        while try_query:
            try:
                if log:
                    log('PROXY SERVICE: get list => %s' % proxy_list_url)
                r = requests.get(proxy_list_url, auth=HTTPBasicAuth(self.user, self.password))
                data = r.json()
                if log:
                    log('PROXY SERVICE: data received => %r' % data)
                if not data['proxy_list']:
                    proxy_list_url = add_or_replace_parameter(proxy_list_url, 'refresh', str(1))
                    r = requests.get(proxy_list_url, auth=HTTPBasicAuth(self.user, self.password))
                    data = r.json()
                    if log:
                        log('PROXY SERVICE: data received => %r' % data)
                proxy_list = data['proxy_list']
            except Exception, e:
                if not (try_no <= 10 and self.retry):
                    raise e
                else:
                    try_no += 1
                    time.sleep(1)
            else:
                try_query = False

        return proxy_list

# -*- coding: utf-8 -*-

import time
import requests
from w3lib.url import urljoin_rfc, add_or_replace_parameter


class Compmon2API(object):

    def __init__(self, host, api_key, retry=True, max_retry_no=10):
        self.host = host
        self.api_key = api_key

        self.retry = retry
        self.max_retry = max_retry_no

    def get_matched_products(self, website_id):
        api_url = urljoin_rfc(self.host, '/api/get_matched_products_paged.json')
        api_url = add_or_replace_parameter(api_url, 'website_id', str(website_id))
        api_url = add_or_replace_parameter(api_url, 'api_key', self.api_key)

        page = 0
        count = 1000
        continue_next_page = True
        matched_products = []

        while continue_next_page:
            api_url = add_or_replace_parameter(api_url, 'start', str(page * count))
            api_url = add_or_replace_parameter(api_url, 'count', str(count))

            try:
                try_no = 1
                try_query = True
                while try_query:
                    try:
                        r = requests.get(api_url)
                        data = r.json()
                        new_matches = data.get('matches', [])
                    except Exception, e:
                        if not (try_no <= 10 and self.retry):
                            raise e
                        else:
                            try_no += 1
                            time.sleep(1)
                    else:
                        try_query = False
            except Exception:
                continue_next_page = False
            else:
                matched_products.extend(new_matches)
                if len(new_matches) < count:
                    continue_next_page = False
                else:
                    page += 1

        return matched_products

    def get_matches_count_website(self, website_id):
        count = 0

        api_url = urljoin_rfc(self.host, '/api/get_matched_products_count.json')
        api_url = add_or_replace_parameter(api_url, 'website_id', str(website_id))
        api_url = add_or_replace_parameter(api_url, 'api_key', self.api_key)

        try_no = 1
        try_query = True
        while try_query:
            try:
                r = requests.get(api_url)
                data = r.json()
                count = data['count']
            except Exception, e:
                if not (try_no <= 10 and self.retry):
                    raise e
                else:
                    try_no += 1
                    time.sleep(1)
            else:
                try_query = False

        return count

    def get_main_website_id(self, member_id):
        main_website_id = 0

        api_url = urljoin_rfc(self.host, '/api/get_account_info.json')
        api_url = add_or_replace_parameter(api_url, 'member_id', str(member_id))
        api_url = add_or_replace_parameter(api_url, 'api_key', self.api_key)

        try_no = 1
        try_query = True
        while try_query:
            try:
                r = requests.get(api_url)
                data = r.json()
                main_website_id = data['main_site']
            except Exception, e:
                if not (try_no <= 10 and self.retry):
                    raise e
                else:
                    try_no += 1
                    time.sleep(1)
            else:
                try_query = False

        return int(main_website_id)

    def get_products_total_account(self, member_id):
        total = 0

        api_url = urljoin_rfc(self.host, '/api/get_products_total_account.json')
        api_url = add_or_replace_parameter(api_url, 'member_id', str(member_id))
        api_url = add_or_replace_parameter(api_url, 'api_key', self.api_key)

        try_no = 1
        try_query = True
        while try_query:
            try:
                r = requests.get(api_url)
                data = r.json()
                total = data['total']
            except Exception, e:
                if not (try_no <= 10 and self.retry):
                    raise e
                else:
                    try_no += 1
                    time.sleep(1)
            else:
                try_query = False

        return int(total)

    def get_match_rate_website(self, website_id):
        rate = 0

        api_url = urljoin_rfc(self.host, '/api/get_match_rate_website.json')
        api_url = add_or_replace_parameter(api_url, 'website_id', str(website_id))
        api_url = add_or_replace_parameter(api_url, 'api_key', self.api_key)

        try_no = 1
        try_query = True
        while try_query:
            try:
                r = requests.get(api_url)
                data = r.json()
                rate = data['rate']
            except Exception, e:
                if not (try_no <= 10 and self.retry):
                    raise e
                else:
                    try_no += 1
                    time.sleep(1)
            else:
                try_query = False

        return rate

    def retrieve_all_products_website(self, website_id, path):
        api_url = urljoin_rfc(self.host, '/api/get_all_products_website_optimized')
        api_url = add_or_replace_parameter(api_url, 'website_id', str(website_id))
        api_url = add_or_replace_parameter(api_url, 'api_key', self.api_key)

        try_no = 1
        try_query = True
        while try_query:
            r = requests.get(api_url, stream=True)
            if r.status_code == 200:
                with open(path, 'wb') as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)
                try_query = False
            else:
                if not (try_no <= 10 and self.retry):
                    raise Exception('Could not retrieve the website products for {}'.format(website_id))
                else:
                    try_no += 1
                    time.sleep(1)

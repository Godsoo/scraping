import csv
import os
import time
import re
import shutil

import random

from scrapy.spider import BaseSpider
from scrapy.http import HtmlResponse
from scrapy.utils.url import url_query_parameter

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from utils import extract_price

from phantomjs import PhantomJS

HERE = os.path.abspath(os.path.dirname(__file__))

from pricecheck import valid_price

from itertools import cycle


class GoogleSpider(BaseSpider):
    name = 'ldmountaincentre-googleapis.com'
    allowed_domains = ['google.co.uk']

    start_urls = ['http://www.google.com']

    errors = []

    F_LAST_RESULTS = 'gshopping_last_results.csv'
    SHOPPING_URL = 'http://www.google.co.uk/shopping?hl=en'

    def __init__(self, *args, **kwargs):
        super(GoogleSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self._browsers = []

        proxies = ['23.19.154.246:3128',
                   '23.19.154.247:3128',
                   '23.19.154.248:3128',
                   '23.19.154.249:3128',
                   '23.19.154.250:3128',
                   '23.19.188.246:3128',
                   '23.19.188.247:3128',
                   '23.19.188.248:3128',
                   '23.19.188.249:3128',
                   '23.19.188.250:3128']

        user_agents = cycle(
            ['Mozilla/5.0 (Windows NT 5.1; rv:24.0) Gecko/20100101 Firefox/24.0',
             'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:24.0) Gecko/20100101 Firefox/24.0',
             'Mozilla/5.0 (Windows NT 6.2; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0',
             'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:24.0) Gecko/20100101 Firefox/24.0',
             'Mozilla/5.0 (X11; Linux x86_64; rv:24.0) Gecko/20100101 Firefox/24.0']
        )

        browser_profiles = []

        for proxy_ip_port in proxies:
            browser_profiles.append(
                 {'proxy': proxy_ip_port,
                  'proxy-type': 'http',
                  'proxy-auth': None}
            )

        for profile in browser_profiles:
            if profile['proxy']:
                proxy = {}
                proxy['host'] = profile['proxy']
                proxy['type'] = profile['proxy-type']
                if profile['proxy-auth']:
                    proxy['auth'] = profile['proxy-auth']
            else:
                proxy = None
            browser = PhantomJS.create_browser(proxy=proxy, user_agent=user_agents.next())
            user_agent = browser.desired_capabilities[u'phantomjs.page.settings.userAgent']
            self._browsers.append({'webdriver': browser,
                                   'useragent': user_agent,
                                   'proxy': profile['proxy']})

        self._today_result_ids = {}
        file_last_results = os.path.join(HERE, self.F_LAST_RESULTS)
        if os.path.exists(file_last_results):
            today = time.gmtime().tm_yday
            last_day = time.gmtime(os.path.getctime(file_last_results)).tm_yday
            if last_day == today:
                shutil.copy(file_last_results, '%s.bak' % file_last_results)
                with open(file_last_results) as f_today:
                    reader = csv.DictReader(f_today)
                    for row in reader:
                        self._today_result_ids[row['identifier']] = row

    def spider_closed(self, spider):
        for browser in self._browsers:
            browser['webdriver'].quit()
        shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(HERE, self.F_LAST_RESULTS))

    def parse(self, response):
        f = open(os.path.join(HERE, 'product_skus.csv'))
        reader = csv.DictReader(f)

        url = self.SHOPPING_URL

        # GET Google Shopping website
        for browser in self._browsers:
            self.log('\n'
                     '>>> PROXY: %s\n'
                     '>>> UA: %s\n'
                     '>>> GET: %s\n' % (browser['proxy'],
                                        browser['useragent'],
                                        url))
            browser['webdriver'].get(url)
            self.log('>>> BROWSER => OK')

        browsers_free = len(self._browsers)

        row = next(reader, None)

        # Search items
        while row is not None:
            # If exists today's results then it loads them
            if row['identifier'] in self._today_result_ids:
                yield self.load_item_(self._today_result_ids[row['identifier']], use_adurl=False)
                row = next(reader, None)  # Next row
                continue
            if browsers_free:
                browsers_free -= 1

                '''
                 if row['sku']:
                     search = row['sku']
                     self.log('>>> Search by SKU: ' + search)
                 else:
                '''
                search = row['name']
                self.log('>>> Search by NAME: ' + search)

                meta = {'sku': row['sku'],
                        'price': row['price'],
                        'identifier': row['identifier']}

                self._browsers[browsers_free]['search'] = search
                self._browsers[browsers_free]['meta'] = meta

            row = next(reader, None)  # Next row

            if browsers_free:
                if row:
                    continue
            else:
                browsers_free = len(self._browsers)

            for browser in self._browsers:
                browser['webdriver'].delete_all_cookies()

            time.sleep(random.choice(range(5, 25)))

            for browser in self._browsers:
                if not browser['search']:
                    continue
                try:
                    self.log('\n'
                             '>>> BROWSER: Clear current search and send new...\n'
                             '>>> PROXY: %s\n'
                             '>>> UA: %s\n'
                             '>>> SEARCH: %s\n' % (browser['proxy'],
                                                   browser['useragent'],
                                                   browser['search']))

                    try:
                        browser['search_input'] = browser['webdriver'].find_element_by_id('gbqfq')
                    except:
                        browser['search_input'] = browser['webdriver'].find_element_by_class_name('gsfi')
                    try:
                        browser['search_button'] = browser['webdriver'].find_element_by_id('gbqfb')
                    except:
                        browser['search_button'] = browser['webdriver'].find_element_by_xpath('//button[@value="Search"]')

                    browser['search_input'].clear()
                    browser['search_input'].send_keys(browser['search'])
                except Exception, e:
                    if browser['search']:
                        self.log('\n>>> ERROR: Failed to search %s\n' % browser['search'])
                        browser['search'] = None
                    # This should be a change in the website style, to save the screenshot and source and not continue
                    browser['webdriver'].save_screenshot(os.path.join(HERE, 'browser_error.png'))
                    with open(os.path.join(HERE, 'browser_error.html'), 'w') as f:
                        f.write(browser['webdriver'].page_source.encode('utf-8'))
                    raise e

            time.sleep(random.choice(range(5, 10)))

            for browser in self._browsers:
                if not browser['search']:
                    continue
                try:
                    self.log('\n'
                             '>>> BROWSER: Click search button...\n'
                             '>>> PROXY: %s\n'
                             '>>> UA: %s\n'
                             '>>> SEARCH: %s\n' % (browser['proxy'],
                                                   browser['useragent'],
                                                   browser['search']))
                    browser['search_button'].click()
                    self.log('>>> BROWSER => OK')
                except Exception, e:
                    self.log(e)
                    if browser['search']:
                        self.log('\n>>> ERROR: Failed to search %s\n' % browser['search'])
                        browser['search'] = None

            time.sleep(random.choice(range(10, 25)))

            browsers_get_more = []

            for i, browser in enumerate(self._browsers):
                if not browser['search']:
                    continue
                browser['item'] = None
                try:
                    products = browser['webdriver'].find_elements_by_xpath('//div[@id="search"]//li[contains(@class, "psli")]')
                    link = None
                    item_url = ''
                    item_found = False
                    for product in products:
                        link = product.find_element_by_xpath('.//h3[contains(@class, "r")]/a')
                        item_url = link.get_attribute('href')
                        if 'ldmountaincentre' not in item_url:
                            item_found = True
                            break  # First valid

                    if not item_found:
                        continue

                    if not link:
                        self.log('Not link')
                        continue

                    name = link.text

                    try:
                        price = product.find_element_by_xpath('.//div[@class="psliprice"]//b').text
                    except:
                        try:
                            price = product.find_element_by_xpath('.//div[contains(@class, "psrpcont")]/span[@class="psrp"]').text
                        except:
                            try:
                                price = product.find_element_by_xpath('.//div[@class="psliprice"]').text
                            except:
                                try:
                                    # Merchant links
                                    price = product.find_element_by_xpath('.//*[@class="psmkprice"]//b').text
                                except Exception, e:
                                    self.errors.append('WARNING: No price searching %s' % browser['search'])
                                    # Go to shopping again
                                    browser['webdriver'].get(self.SHOPPING_URL)
                                    time.sleep(random.choice(range(5, 10)))
                                    raise e
                    try:
                        more_stores = re.findall(r'from \d+\+ stores',
                                                 product.find_element_by_xpath('.//div[contains(@class, "_tyb")]').text)
                    except:
                        try:
                            more_stores = re.findall(r'from \d+ shops',
                                                     product.find_element_by_xpath('.//div[contains(@class, "_tyb")]').text)
                        except:
                            try:
                                more_stores = re.findall(r'from \d+\+ stores', product.text)
                            except:
                                try:
                                    more_stores = re.findall(r'from \d+ shops', product.text)
                                except:
                                    more_stores = None

                    item = {'name': name,
                            'url': item_url,
                            'link': link}
                    if more_stores:
                        browser['item'] = item
                        browsers_get_more.append(i)
                        self.log('\n'
                                 '>>> PROXY: %s\n'
                                 '>>> UA: %s\n'
                                 '>>> ITEM FOUND: %s\n'
                                 '>>> MORE STORES: %s\n' % (browser['proxy'],
                                                            browser['useragent'],
                                                            item['name'],
                                                            item['url']))
                    else:
                        item['price'] = extract_price(price)
                        if valid_price(browser['meta']['price'], item['price']):
                            self.log('\n'
                                     '>>> PROXY: %s\n'
                                     '>>> UA: %s\n'
                                     '>>> ITEM FOUND: %s\n'
                                     '>>> ITEM PRICE: %s\n' % (browser['proxy'],
                                                               browser['useragent'],
                                                               item['name'],
                                                               item['price']))
                            yield self.load_item_(item, browser)
                except Exception, e:
                    self.log('>>>> ERROR IN %s' % browser['webdriver'].current_url)
                    self.log('>>>> %s' % e)
                    if browser['search']:
                        self.log('\n>>> ERROR: Failed to search %s\n' % browser['search'])
                        browser['search'] = None
                    # This should be a change in the website style, to save the screenshot and source and not continue
                    browser['webdriver'].save_screenshot(os.path.join(HERE, 'browser_error.png'))
                    with open(os.path.join(HERE, 'browser_error.html'), 'w') as f:
                        f.write(browser['webdriver'].page_source.encode('utf-8'))

            if browsers_get_more:
                for b in browsers_get_more:
                    browser = self._browsers[b]
                    self.log('\n'
                             '>>> PROXY: %s\n'
                             '>>> UA: %s\n'
                             '>>> ITEM NAME: %s\n'
                             '>>> GET: %s\n' % (browser['proxy'],
                                                browser['useragent'],
                                                browser['item']['name'],
                                                browser['item']['url']))
                    browser['item']['link'].click()
                    # browser['webdriver'].get(browser['item']['url'])
                    self.log('>>> BROWSER => OK')

                time.sleep(random.choice(range(10, 25)))

                for b in browsers_get_more:
                    try:
                        browser = self._browsers[b]
                        base_price = browser['webdriver'].find_element_by_id('os-price-col-th')
                        base_price.click()
                    except:
                        try:
                            try:
                                # Google has shown a popup, we locate the link that leads to the price comparison
                                compare_link = browser['webdriver']\
                                    .find_element_by_xpath('//li[contains(@class, "pspo-popout")]'
                                                           '//a[contains(@class, "pspo-compare-price")]')
                                compare_link.click()
                            except:
                                browser['webdriver'].get(browser['item']['url'])  # Force get item page
                                time.sleep(5)
                            time.sleep(random.choice(range(5, 10)))
                            # Try order by price again
                            base_price = browser['webdriver'].find_element_by_id('os-price-col-th')
                            base_price.click()
                        except Exception, e:
                            if browser['search']:
                                self.log('\n>>> ERROR: Failed to search %s\n' % browser['search'])
                                browser['search'] = None
                            # This should be a change in the website style, to save the screenshot and source and not continue
                            browser['webdriver'].save_screenshot(os.path.join(HERE, 'browser_error.png'))
                            with open(os.path.join(HERE, 'browser_error.html'), 'w') as f:
                                f.write(browser['webdriver'].page_source.encode('utf-8'))
                            raise e

                time.sleep(random.choice(range(5, 10)))

                for b in browsers_get_more:
                    browser = self._browsers[b]

                    try:
                        price = None
                        seller = None
                        item_url = None
                        osrows = browser['webdriver'].find_elements_by_class_name('os-row')
                        for osrow in osrows:
                            seller = osrow.find_element_by_class_name('os-seller-name-primary')
                            item_url = seller.find_element_by_tag_name('a').get_attribute('href')
                            seller_name = seller.find_element_by_tag_name('a').text
                            if 'ldmountaincentre' not in item_url:
                                price = extract_price(osrow.find_element_by_class_name('os-base_price').text)
                                shipping_cost = extract_price(osrow.find_element_by_class_name('os-total-description').text)
                                break
                        if price:
                            if valid_price(browser['meta']['price'], price):
                                item = browser['item']
                                item['price'] = price
                                item['shipping_cost'] = shipping_cost
                                item['url'] = item_url
                                item['dealer'] = seller_name
                                yield self.load_item_(item, browser)
                        else:
                            self.errors.append('WARNING: No price in %s' % browser['webdriver'].current_url)
                    except Exception, e:
                        if browser['search']:
                            self.log('\n>>> ERROR: Failed to search %s\n' % browser['search'])
                            browser['search'] = None
                        # This should be a change in the website style, to save the screenshot and source and not continue
                        browser['webdriver'].save_screenshot(os.path.join(HERE, 'browser_error.png'))
                        with open(os.path.join(HERE, 'browser_error.html'), 'w') as f:
                            f.write(browser['webdriver'].page_source.encode('utf-8'))
                        raise e

            # Set search to None
            for browser in self._browsers:
                browser['search'] = None

    def load_item_(self, item, browser=None, use_adurl=True):
        if browser:
            response = HtmlResponse(url=browser['webdriver'].current_url,
                                    body=browser['webdriver'].page_source,
                                    encoding='utf-8')
        else:
            response = HtmlResponse(url='http://www.google.co.uk/shopping',
                                    body='<html></html>',
                                    encoding='utf-8')
        l = ProductLoader(item=Product(), response=response)
        l.add_value('name', self._try_encoding(item['name']))

        # Item URL
        url = self._try_encoding(item['url'])
        adurl = url_query_parameter(url, 'adurl')
        if adurl and use_adurl:
            item_url = adurl
        else:
            item_url = url

        l.add_value('url', item_url)
        l.add_value('price', item['price'])
        l.add_value('shipping_cost', item.get('shipping_cost', 0))
        l.add_value('dealer', item.get('dealer', ''))
        l.add_value('identifier', browser['meta']['identifier'] if browser else item['identifier'])
        l.add_value('sku', browser['meta']['sku'] if browser else item['sku'])

        return l.load_item()

    def _try_encoding(self, value):
        try:
            value = value.encode('utf-8')
        except:
            pass
        return value.decode('utf-8')

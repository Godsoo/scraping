"""
Name: Google Shopping Base Spider
Original developer: Emiliano M. Rudenick <emr.frei@gmail.com>

IMPORTANT:

- Local proxies management. It uses Proxy Service.
- Use of PhantomJS to browse the website.
- PLEASE be CAREFUL, Google bans the proxies quickly.
"""


import os
import time
import random
from datetime import datetime
from httplib import BadStatusLine
from urllib2 import URLError
from socket import error as SocketError

from scrapy import Spider, Selector
from scrapy import log
from scrapy.http import HtmlResponse
from scrapy.utils.url import url_query_parameter, urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.item import Item, Field
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from phantomjs import PhantomJS

from itertools import cycle

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)
from product_spiders.utils import extract_price

from product_spiders.contrib.proxyservice import ProxyServiceAPI
from product_spiders.config import (
    PROXY_SERVICE_HOST,
    PROXY_SERVICE_USER,
    PROXY_SERVICE_PSWD,
)


PROXY_SERVICE_TARGET_ID = 135
HERE = os.path.abspath(os.path.dirname(__file__))


class Review(Item):
    date = Field()
    rating = Field()
    full_text = Field()
    url = Field()


class GoogleShoppingBaseSpider(Spider):
    name = 'google-shopping.spider'
    allowed_domains = ['google.com']
    start_urls = ['https://www.google.com/shopping?hl=en']

    # proxy service
    proxy_service_target_id = 135
    proxy_service_location = None

    # US Shopping
    # Change this if the spider must collect results from a different location
    GOOGLE_DOMAIN = 'google.com'
    SHOPPING_URL = 'https://www.google.com/shopping?hl=en'

    # Number of open PhantomJS browsers in use
    ACTIVE_BROWSERS = 20
    # User Agents to use. You can overwrite this to use different User Agents
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1',
        'Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; rv:33.0) Gecko/20100101 Firefox/33.0',
        'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:24.0) Gecko/20100101 Firefox/24.0',
        'Mozilla/5.0 (X11; Linux i586; rv:31.0) Gecko/20100101 Firefox/31.0',
        'Mozilla/5.0 (X11; Linux x86_64; rv:24.0) Gecko/20100101 Firefox/24.0',
        'Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:24.0) Gecko/20100101 Firefox/24.0']

    # Set it to False if the spider must parse only lowest priced products
    parse_all = True
    # Set it to True if spider must to parse reviews
    parse_reviews = False

    # collect Part Number as SKU
    part_number_as_sku = False
    # collect GTIN as SKU
    gtin_as_sku = False

    # list of sellers to exclude by name
    exclude_sellers = []

    # Include only sellers
    filter_sellers = []

    pages_to_process = 1

    errors = []

    def __init__(self, *args, **kwargs):
        super(GoogleShoppingBaseSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self._browsers = []
        self._browsers_free = []
        self.base_url = ''
        self.user_agents = cycle(self.USER_AGENTS)

        self._init_browsers()

        self._yielded_products = set()

    def _init_browsers(self):
        for browser_ix in range(self.ACTIVE_BROWSERS):
            self.renew_browser()

    def spider_closed(self, spider):
        for browser in self._browsers:
            browser['webdriver'].quit()

    def search_iterator(self):
        """
        Must return a tuple with the following values:
        (<search:string:required>,
         <row:dict:optional>,
         <fields to copy:list:optional>)

        So the spider will be searching by `search`
        then will look at `fields to copy` and
        will take the values from `row` and
        copy those into the resulting Item object.

        `fields to copy` can be None
        `row` is required if `fields to copy` is not None
        If `fields to copy` is not None and `row` is None
        then `fields to copy` will be ignored.
        """
        raise NotImplementedError('Spider must implement `search_iterator`')

    def match_item(self, item):
        """
        Must return True or False
        If False then the item will be ignored.
        """
        return True

    def _init_search_delete_cookies(self):
        """
        Init search: delete cookies
        """
        for browser in self._browsers:
            try:
                browser['webdriver'].delete_all_cookies()
            except:
                self.renew_browser(browser, True)
            if browser['retry']:
                url = self.SHOPPING_URL
                # Get home page again
                self.log('\n'
                         '>>> PROXY: %s\n'
                         '>>> UA: %s\n'
                         '>>> GET: %s\n' % (browser['proxy'],
                                            browser['useragent'],
                                            url))
                try:
                    browser['webdriver'].get(url)
                except (SocketError, URLError, BadStatusLine, TimeoutException) as e:
                    self.log("Failed to renew cookies for browser with Proxy: {} (id: {})".format(
                        browser['proxy'], browser['proxy_id']),
                        level=log.ERROR)
                    self.log("Error: {}".format(str(e)))
                    self.renew_browser(browser, browser_blocked=True)
                except IOError as e:
                    self.log("Got IOError when doing renew cookies for browser with Proxy: {} (id: {})".format(
                        browser['proxy'], browser['proxy_id']),
                        level=log.ERROR)
                    self.log("Error: {}".format(str(e)))
                    self.renew_browser(browser, browser_blocked=True)
                else:
                    self.log('>>> BROWSER => OK')

    def _init_search_populate_search(self):
        """
        Init search: populate input search with new value
        """
        for browser in self._browsers:
            if not browser.get('search', None):
                continue

            if browser['retry']:
                self.log('\nRETRYING: %s' % browser['search'])
                browser['retry'] = False

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
                except NoSuchElementException:
                    browser['search_input'] = browser['webdriver'].find_element_by_class_name('gsfi')
                try:
                    browser['search_button'] = browser['webdriver'].find_element_by_id('gbqfb')
                except NoSuchElementException:
                    try:
                        browser['search_button'] = browser['webdriver'].find_element_by_xpath('//button[@value="Search"]')
                    except NoSuchElementException:
                        browser['search_button'] = browser['webdriver'].find_element_by_xpath('//button[@class="lsb"]')

                browser['search_input'].clear()
                browser['search_input'].send_keys(browser['search'])
            except (NoSuchElementException, SocketError, URLError, BadStatusLine, TimeoutException) as e:
                self.log("Failed when getting search input or search button with browser with Proxy: {} (id: {})".format(
                    browser['proxy'], browser['proxy_id']),
                    level=log.ERROR)
                self.log("Error: {}".format(str(e)))
                self.renew_browser(browser, browser_blocked=True)
            except Exception, e:
                browser_blocked = self._is_blocked(browser)
                if not browser_blocked:
                    if browser.get('search', None):
                        self.log('\n>>> ERROR: Failed to search %s\n' % browser['search'])
                        browser['search'] = None
                    self.log('ERROR: %s' % e)
                else:
                    self.renew_browser(browser, True)

    def _init_search_submit(self):
        """
        Init search: submit new search
        """
        for browser in self._browsers:
            if not browser.get('search', None) or browser.get('retry', False):
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
            except (SocketError, URLError, BadStatusLine, TimeoutException) as e:
                self.log("Failed when clicking search button with browser with Proxy: {} (id: {})".format(
                    browser['proxy'], browser['proxy_id']),
                    level=log.ERROR)
                self.log("Error: {}".format(str(e)))
                self.renew_browser(browser, browser_blocked=True)
            except Exception, e:
                browser_blocked = self._is_blocked(browser)
                if not browser_blocked:
                    self.log(e)
                    if browser.get('search', None):
                        self.log('\n>>> ERROR: Failed to search %s\n' % browser['search'])
                        browser['search'] = None
                else:
                    self.renew_browser(browser, True)

    def _process_search_results_page_browser(self, browser):
        get_more = False
        try:
            hxs = Selector(text=browser['webdriver'].page_source)
        except (SocketError, URLError, BadStatusLine, TimeoutException) as e:
            self.log("Failed when getting Selector for search results with browser with Proxy: {} (id: {})".format(
                browser['proxy'], browser['proxy_id']),
                level=log.ERROR)
            self.log("Error: {}".format(str(e)))
            self.renew_browser(browser, browser_blocked=True)
            return False
        except IOError as e:
            self.log("Got IOError when getting selector for search results with browser with Proxy: {} (id: {})".format(
                browser['proxy'], browser['proxy_id']),
                level=log.ERROR)
            self.log("Error: {}".format(str(e)))
            self.renew_browser(browser, browser_blocked=True)
            return False

        if self.filter_sellers:
            try:
                sellers = set(hxs.xpath('//div[@class="sr__group"]/div[@class="sr__title" '
                                        'and text()="Seller"]/following-sibling::div//'
                                        'span[@class="sr__link-text"]/text()').extract())
            except:
                self.log('Error: Seller filter not found')
            else:
                browser['sellers_found'] = []
                for s in sellers:
                    if s in self.filter_sellers:
                        browser['sellers_found'].append(s)
                if not browser['sellers_found']:
                    return False

        products = hxs.xpath('//div[@id="search"]//div[@data-docid and contains(@class, "psli")]')
        if not products:
            products = hxs.xpath('//div[@id="search"]//div[contains(@class, "g")]')
        if not products:
            products = hxs.xpath('//div[@id="search"]//div[contains(@class, "pslmain")]')
        if not products:
            # Go to shopping again
            self.log('WARNING: No products in %s' % browser['webdriver'].current_url)
            # browser['webdriver'].get(self.SHOPPING_URL)
            browser['retry'] = True
            # time.sleep(random.choice(range(5, 10)))
            return False

        for product_xs in products:
            link = product_xs.xpath('.//h3[contains(@class, "r")]/a')
            if not link:
                link = product_xs.xpath('.//h3/a[@class="pstl"]')
                if not link:
                    # Go to shopping again
                    self.log('WARNING: No link in %s' % browser['webdriver'].current_url)
                    continue

            item_url = link.xpath('@href').extract()[0]
            data_cid = product_xs.xpath('.//*/@data-cid').extract()
            more_store_url = product_xs.xpath('.//*/@href').re(r'/shopping/product/\d+')
            if more_store_url:
                item_url = urljoin_rfc(self.base_url, more_store_url[0])
            reviews_found = bool(product_xs.xpath('.//a[contains(@class, "sg-rating__product")]'))
            if not reviews_found:
                reviews_found = bool(product_xs.xpath('.//a[contains(@class, "sh-rt__product")]'))
            reviews_url = ''
            if reviews_found and data_cid:
                reviews_url = urljoin_rfc(self.base_url, '/shopping/product/%s/reviews' % data_cid[0])
                if reviews_found:
                    self.log('Reviews found => %s' % reviews_url)
            try:
                name = link.xpath('text()').extract()[0]
                identifier = product_xs.xpath('@data-docid').extract()[0]
            except IndexError:
                self.log('No Name or Identifier in => %s' % browser['webdriver'].current_url)
                continue

            price = product_xs.xpath('.//div[@class="pslline"]//b/text()').extract()
            if not price:
                price = product_xs.xpath('.//div[@class="psgextra"]//b/text()').extract()
            if not price:
                price = product_xs.xpath('.//div[contains(@class, "psrpcont")]/span[@class="psrp"]/text()').extract()
            if not price:
                price = product_xs.xpath('.//div[@class="psliprice"]/text()').extract()
            if not price:
                # Merchant links
                price = product_xs.xpath('.//*[@class="psmkprice"]//b/text()').extract()
            if not price:
                self.log('NO PRICE IN %s' % browser['webdriver'].current_url)

            item = {'name': name,
                    'link': link,
                    'url': item_url,
                    'all_stores': None,
                    'identifier': identifier,
                    'reviews_url': reviews_url}

            if more_store_url:
                browser['items'].append(item)
                get_more = True
                self.log('\n'
                         '>>> PROXY: %s\n'
                         '>>> UA: %s\n'
                         '>>> ITEM FOUND: %s\n'
                         '>>> MORE STORES: %s\n' % (browser['proxy'],
                                                    browser['useragent'],
                                                    item['name'],
                                                    item['url']))
            else:
                item['price'] = extract_price(price[0])
                try:
                    seller = product_xs.xpath('.//*[contains(@class, "_tyb")]/text()').extract()[0]
                except IndexError:
                    self.log('ERROR: No seller in %s' % browser['webdriver'].current_url)
                    continue
                item['dealer'] = seller.split(' from ')[-1]
                self.log('\n'
                         '>>> PROXY: %s\n'
                         '>>> UA: %s\n'
                         '>>> ITEM FOUND: %s\n'
                         '>>> ITEM PRICE: %s\n' % (browser['proxy'],
                                                   browser['useragent'],
                                                   item['name'],
                                                   item['price']))
                browser['items_collected'] \
                    .append(self.load_item_(item, browser))
        return get_more

    def _parse_search_results(self):
        """
        Search results: Parse search results and "get more stores" links
        """
        browsers_get_more = set()
        for i, browser in enumerate(self._browsers):
            if (not browser.get('search', None)) or browser.get('retry', False):
                continue
            browser['items'] = []
            get_more = False
            get_more |= self._process_search_results_page_browser(browser)
            if self.pages_to_process and self.pages_to_process > 1:
                current_page = 1
                while current_page < self.pages_to_process:
                    try:
                        next_link = browser['webdriver'].find_element_by_id('pnnext')
                    except NoSuchElementException:
                        self.log('\n'
                                 '>>> BROWSER: Reached last page %d...\n'
                                 '>>> PROXY: %s\n'
                                 '>>> UA: %s\n'
                                 '>>> SEARCH: %s\n' % (current_page,
                                                       browser['proxy'],
                                                       browser['useragent'],
                                                       browser['search']))
                        break
                    except (SocketError, URLError, BadStatusLine, TimeoutException) as e:
                        self.log("Failed when clicking \"next\" for search results with browser with Proxy: {} (id: {})".format(
                            browser['proxy'], browser['proxy_id']),
                            level=log.ERROR)
                        self.log("Error: {}".format(str(e)))
                        self.renew_browser(browser, browser_blocked=True)
                        break
                    except IOError as e:
                        self.log("Got IOError when clicking \"next\" for search results with browser with Proxy: {} (id: {})".format(
                            browser['proxy'], browser['proxy_id']),
                            level=log.ERROR)
                        self.log("Error: {}".format(str(e)))
                        self.renew_browser(browser, browser_blocked=True)
                        break
                    try:
                        self.log('\n'
                                 '>>> BROWSER: Click next button from page %d...\n'
                                 '>>> PROXY: %s\n'
                                 '>>> UA: %s\n'
                                 '>>> SEARCH: %s\n' % (current_page,
                                                       browser['proxy'],
                                                       browser['useragent'],
                                                       browser['search']))
                        next_link.click()
                        self.log('>>> BROWSER => OK')
                    except (SocketError, URLError, BadStatusLine, TimeoutException) as e:
                        self.log("Failed when clicking \"next\" for search results with browser with Proxy: {} (id: {})".format(
                            browser['proxy'], browser['proxy_id']),
                            level=log.ERROR)
                        self.log("Error: {}".format(str(e)))
                        self.renew_browser(browser, browser_blocked=True)
                        break
                    except IOError as e:
                        self.log("Got IOError when clicking \"next\" for search results with browser with Proxy: {} (id: {})".format(
                            browser['proxy'], browser['proxy_id']),
                            level=log.ERROR)
                        self.log("Error: {}".format(str(e)))
                        self.renew_browser(browser, browser_blocked=True)
                        break
                    except Exception, e:
                        browser_blocked = self._is_blocked(browser)
                        if not browser_blocked:
                            self.log(e)
                            if browser.get('search', None):
                                self.log('\n>>> ERROR: Failed to search %s\n' % browser['search'])
                                browser['retry'] = True
                        else:
                            self.renew_browser(browser, True)
                            break
                    time.sleep(random.choice(range(10, 25)))
                    get_more |= self._process_search_results_page_browser(browser)
                    current_page += 1

            if get_more:
                browsers_get_more.add(i)
        return browsers_get_more

    def browser_should_continue(self, browser):
        if self.filter_sellers and browser.get('sellers_found'):
            browser['items_collected'] = filter(lambda i: bool(i), browser['items_collected'])
            sellers_collected = [i['dealer'] for i in browser['items_collected']]
            all_collected = all(s in sellers_collected for s in browser['sellers_found'])
            if all_collected:
                return False
        return True

    def _process_more_results_page_browser(self, browser):
        for item in browser['items']:
            self.log('\n'
                     '>>> PROXY: %s\n'
                     '>>> UA: %s\n'
                     '>>> ITEM NAME: %s\n'
                     '>>> GET: %s\n' % (browser['proxy'],
                                        browser['useragent'],
                                        item['name'],
                                        item['url']))

            browser['webdriver'].get(item['url'])
            self.log('>>> BROWSER => OK')

            time.sleep(random.choice(range(10, 25)))

            try:
                all_stores = browser['webdriver'] \
                    .find_element_by_xpath('.//a[@class="pag-detail-link" '
                                           'and contains(text(), "online stores")]')
            except NoSuchElementException:
                try:
                    all_stores = browser['webdriver'] \
                        .find_element_by_xpath('.//a[@class="pag-detail-link" '
                                               'and contains(text(), "online shops")]')
                except NoSuchElementException:
                    all_stores = None

            self.log('\n'
                     '>>> PROXY: %s\n'
                     '>>> UA: %s\n'
                     '>>> ITEM FOUND: %s\n'
                     '>>> ALL STORES: %s\n' % (browser['proxy'],
                                               browser['useragent'],
                                               item['name'],
                                               all_stores if all_stores else ''))

            if all_stores:
                all_stores.click()
                self.log('>>> BROWSER => OK')

                time.sleep(random.choice(range(10, 25)))

            try:
                hxs = Selector(text=browser['webdriver'].page_source)
            except (SocketError, URLError, BadStatusLine, TimeoutException) as e:
                self.log("Failed to get Selector for browser with Proxy: {} (id: {})".format(
                    browser['proxy'], browser['proxy_id']),
                    level=log.ERROR)
                self.log("Error: {}".format(str(e)))
                return False
            except IOError as e:
                self.log("Got IOError when doing get Selector for browser with Proxy: {} (id: {})".format(
                    browser['proxy'], browser['proxy_id']),
                    level=log.ERROR)
                self.log("Error: {}".format(str(e)))
                return False

            sku = None
            if not sku:
                if self.part_number_as_sku:
                    part_number = hxs.xpath('//tr[@class="specs-list"]'
                                            '[td[@class="specs-name"][contains(text(), "Part Number")]]'
                                            '/td[@class="specs-value"]/text()').extract_first()
                    if not part_number:
                        part_number = hxs.xpath('//div[@id="specs"]//'
                                                'div[@class="specs-row"]'
                                                '[span[@class="specs-name"][text()="Part Number"]]'
                                                '/span[@class="specs-value"]/text()').extract_first()
                    if part_number:
                        sku = part_number
            if not sku:
                if self.gtin_as_sku:
                    gtin = hxs.xpath('//tr[@class="specs-list"][td[@class="specs-name"][contains(text(), "GTIN")]]'
                                     '/td[@class="specs-value"]/text()').extract_first()
                    if not gtin:
                        gtin = hxs.xpath('//div[@id="specs"]//'
                                         'div[@class="specs-row"]'
                                         '[span[@class="specs-name"][text()="GTIN"]]/'
                                         'span[@class="specs-value"]/text()').extract_first()
                    if gtin:
                        sku = gtin

            if sku:
                item['sku'] = sku

            brand = hxs.xpath('//tr[@class="specs-list"][td[@class="specs-name"][contains(text(), "Brand")]]'
                              '/td[@class="specs-value"]/text()').extract_first()
            if brand:
                item['brand'] = brand

            price = None
            seller = None
            item_url = None
            next_page = True
            while next_page:
                osrows = browser['webdriver'].find_elements_by_class_name('os-row')
                if not osrows:
                    next_page = False
                for osrow in osrows:
                    new_item = item.copy()
                    seller = osrow.find_element_by_class_name('os-seller-name-primary')
                    item_url = seller.find_element_by_tag_name('a').get_attribute('href')
                    seller_name = seller.find_element_by_tag_name('a').text
                    if seller_name in self.exclude_sellers:
                        continue
                    if self.filter_sellers and (seller_name not in self.filter_sellers):
                        continue
                    price = extract_price(osrow.find_element_by_class_name('os-base_price').text)
                    shipping_cost = extract_price(osrow.find_element_by_class_name('os-total-description').text)
                    if price:
                        identifier = item['identifier']
                        new_item['price'] = price
                        new_item['identifier'] = identifier + '-' + seller_name
                        new_item['shipping_cost'] = shipping_cost
                        new_item['url'] = item_url
                        new_item['dealer'] = seller_name
                        for key, value in self._scrape_osrow_additional(new_item, osrow).items():
                            new_item[key] = value
                        browser['items_collected'] \
                            .append(self.load_item_(new_item, browser))

                if not self.browser_should_continue(browser):
                    next_page = False

                if next_page:
                    try:
                        next_sellers_link = browser['webdriver'] \
                            .find_element_by_xpath('//div[@id="online-next-btn" and '
                                                   'not(contains(@class, "button-disabled"))]')
                        next_sellers_link.click()
                        self.log('>>> BROWSER => NEXT SELLERS FOUND FOR %s' % item['identifier'])
                        time.sleep(random.choice(range(10, 25)))
                    except Exception, e:
                        self.log('>>> END OF PAGINATION: %r' % e)
                        next_page = False
        return True

    def _parse_get_more_results(self, browsers_get_more):
        # More stores links
        # Click "get more" links
        failed_browsers = []
        for b in browsers_get_more:
            browser = self._browsers[b]
            try:
                if not self._process_more_results_page_browser(browser):
                    failed_browsers.append(browser)
            except (SocketError, URLError, BadStatusLine, TimeoutException) as e:
                self.log("Failed when processing \"more results\" by browser with Proxy: {} (id: {})".format(
                    browser['proxy'], browser['proxy_id']),
                    level=log.ERROR)
                self.log("Error: {}".format(str(e)))
                failed_browsers.append(browser)
            except IOError as e:
                self.log("Got IOError when processing \"more results\" by browser with Proxy: {} (id: {})".format(
                    browser['proxy'], browser['proxy_id']),
                    level=log.ERROR)
                self.log("Error: {}".format(str(e)))
                failed_browsers.append(browser)
        for browser in failed_browsers:
            self.renew_browser(browser, browser_blocked=True)

    def _scrape_osrow_additional(self, item, osrow):
        """
        Here you can add code to scrape additional data from osrow
        :param osrow:
        :return:
        """
        return {}

    def _parse_reviews(self):
        """
        Parse reviews and append it to each of the items collected
        """
        for i, browser in enumerate(self._browsers):
            if (not browser.get('search', None)) or browser.get('retry', False):
                continue
            for item in browser['items']:
                if not item.get('reviews_url'):
                    continue
                next_page = True
                next_page_url = item['reviews_url']
                reviews = []
                while next_page:
                    self.log('\n'
                             '>>> PROXY: %s\n'
                             '>>> UA: %s\n'
                             '>>> ITEM NAME: %s\n'
                             '>>> GET REVIEWS: %s\n' % (browser['proxy'],
                                                        browser['useragent'],
                                                        item['name'],
                                                        next_page_url))

                    browser['webdriver'].get(next_page_url)
                    self.log('>>> BROWSER => OK')

                    time.sleep(random.choice(range(10, 25)))

                    # Parse reviews
                    hxs = Selector(text=browser['webdriver'].page_source)
                    for review_xs in hxs.xpath('//div[@class="_dpc"]'):
                        new_review = Review()
                        new_review['date'] = datetime.strptime(
                            review_xs.xpath('.//div[@class="shop__secondary"]/text()').extract()[0],
                            '%B %d, %Y').strftime('%d/%m/%Y')
                        new_review['rating'] = review_xs.xpath('.//div[@class="_BYh"]/span/div/@aria-label').extract()[0]
                        new_review['full_text'] = '\n'.join(
                            review_xs.xpath('.//span[@class="_hSb"]/text()|.//div[@class="_cX"]//text()')
                            .extract())
                        new_review['url'] = browser['webdriver'].current_url
                        reviews.append(new_review)

                    next_page_url = hxs.xpath('//div[@id="reviews-next-btn"]/@data-reload').extract()
                    if not next_page_url:
                        next_page = False
                    else:
                        next_page_url = urljoin_rfc(self.base_url, next_page_url[0])

                # Append reviews to Items metadata
                for item_obj in browser['items_collected']:
                    if 'metadata' not in item_obj:
                        item_obj['metadata'] = {}
                    item_obj['metadata']['reviews'] = reviews

    def _collected_items(self):
        for i, browser in enumerate(self._browsers):
            if (not browser.get('search', None)) or browser.get('retry', False):
                continue
            lowest_item = None
            for item in browser['items_collected']:
                if not self.match_item(item):
                    continue
                if self.parse_all:
                    yield item
                else:
                    if lowest_item is None and item['price']:
                        lowest_item = item
                    elif item['price'] and (item['price'] < lowest_item['price']):
                        lowest_item = item
            if (not self.parse_all) and (lowest_item is not None):
                yield lowest_item

    def _set_search_none(self):
        # Set search to None
        for i, browser in enumerate(self._browsers):
            retry = browser.get('retry', False)
            retry_count = int(browser.get('retry_count', 0)) + 1
            if (not retry) or (retry and retry_count > 10):
                self._browsers_free.append(i)
                browser['search'] = None
                if retry_count:
                    browser['retry_count'] = 0
            else:
                browser['retry_count'] = retry_count

    def _are_there_active_searches(self):
        """
        It checks for any active search.
        It supposes that all the inactive searches have already been set as None
        """
        return any([b.get('search', None) is not None for b in self._browsers])

    def parse(self, response):
        if not self.base_url:
            self.base_url = get_base_url(response)

        url = self.SHOPPING_URL

        # GET Google Shopping website
        for browser in self._browsers:
            self.log('\n'
                     '>>> PROXY: %s\n'
                     '>>> UA: %s\n'
                     '>>> GET: %s\n' % (browser['proxy'],
                                        browser['useragent'],
                                        url))
            try:
                browser['webdriver'].get(url)
            except (SocketError, URLError, BadStatusLine, TimeoutException) as e:
                self.log("Failed to load initial URL by browser with Proxy: {} (id: {})".format(
                    browser['proxy'], browser['proxy_id']),
                    level=log.ERROR)
                self.log("Error: {}".format(str(e)))
                self.renew_browser(browser, browser_blocked=True)
            except IOError as e:
                self.log("Got IOError when loading initial URL by browser with Proxy: {} (id: {})".format(
                    browser['proxy'], browser['proxy_id']),
                    level=log.ERROR)
                self.log("Error: {}".format(str(e)))
                self.renew_browser(browser, browser_blocked=True)
            else:
                self.log('>>> BROWSER => OK')

        self._browsers_free = range(len(self._browsers))
        if not self._browsers_free:
            # Finish because there is not active browser
            return

        search_iterator = self.search_iterator()
        search, row, fields = next(search_iterator, (None, None, None))
        # Search items
        while search is not None or self._are_there_active_searches():
            if search is not None and self._browsers_free:

                browser_ix = self._browsers_free.pop()

                self.log('>>> Search by SKU: ' + search)

                meta = {}
                if fields is not None:
                    for field in fields:
                        meta[field] = row[field]

                self._browsers[browser_ix]['search'] = search
                self._browsers[browser_ix]['meta'] = meta
                self._browsers[browser_ix]['items_collected'] = []

                search, row, fields = next(search_iterator, (None, None, None))  # Next row
                if row and self._browsers_free:
                    # Continue if still free browsers to use for next search
                    continue

            self._init_search_delete_cookies()
            time.sleep(random.choice(range(5, 25)))
            self._init_search_populate_search()
            time.sleep(random.choice(range(5, 10)))
            self._init_search_submit()
            time.sleep(random.choice(range(10, 25)))

            browsers_get_more = self._parse_search_results()
            self._parse_get_more_results(browsers_get_more)
            if self.parse_reviews:
                self._parse_reviews()

            time.sleep(random.choice(range(10, 25)))

            # Collect products
            for item in self._collected_items():
                if item and (item['identifier'] not in self._yielded_products):
                    yield item
                    self._yielded_products.add(item['identifier'])

            self._set_search_none()

    def load_item_(self, item, browser, use_adurl=True):
        response = HtmlResponse(url=browser['webdriver'].current_url,
                                body=browser['webdriver'].page_source,
                                encoding='utf-8')

        l = ProductLoader(item=Product(), response=response)
        l.add_value('name', self._try_encoding(item['name']))
        l.add_value('brand', self._try_encoding(item.get('brand', '')))

        # Item URL
        url = self._try_encoding(item['url'])
        adurl = url_query_parameter(url, 'adurl')
        if adurl and use_adurl:
            item_url = adurl
        else:
            item_url = url

        dest_url = url_query_parameter(item_url, 'ds_dest_url') or url_query_parameter(item_url, 'url')
        if dest_url:
            item_url = dest_url

        if ('%s/url' % self.GOOGLE_DOMAIN) in item_url:
            url_q = url_query_parameter(item_url, 'q')
            if not url_q:
                url_q = url_query_parameter(item_url, 'url')
            if url_q:
                item_url = url_q

        l.add_value('url', item_url)
        l.add_value('price', item['price'])
        l.add_value('shipping_cost', item.get('shipping_cost', 0))
        l.add_value('dealer', item.get('dealer', ''))
        l.add_value('identifier', item['identifier'])
        l.add_value('sku', item.get('sku'))
        if 'meta' in browser:
            for k, v in browser['meta'].items():
                l.add_value(k, v)

        res = l.load_item()
        if 'metadata' in item:
            res['metadata'] = item['metadata']

        return res

    def _try_encoding(self, value):
        try:
            value = value.encode('utf-8')
        except:
            pass
        return value.decode('utf-8')

    def renew_browser(self, browser_profile=None, browser_blocked=False):
        proxy_service_api = ProxyServiceAPI(host=PROXY_SERVICE_HOST, user=PROXY_SERVICE_USER, password=PROXY_SERVICE_PSWD)
        blocked = []

        if browser_profile:
            browser_profile['webdriver'].quit()
            if browser_blocked:
                blocked.append(browser_profile['proxy_id'])
        else:
            browser_profile = {}

        proxy = None
        proxy_data = {'id': '', 'url': ''}
        proxy_list = proxy_service_api.get_proxy_list(self.proxy_service_target_id,
                                                      locations=self.proxy_service_location,
                                                      types='https', blocked=blocked, log=self.log, length=1)
        if proxy_list:
            proxy_data = proxy_list[0]
            proxy_type, proxy_host = proxy_data['url'].split('://')
            proxy = {
                'host': proxy_host,
                'type': proxy_type,
            }

        user_agent = self.user_agents.next()
        browser = PhantomJS(proxy=proxy, user_agent=user_agent, load_images=False)

        browser_profile.update(
            {'webdriver': browser.driver,
             'useragent': user_agent,
             'proxy': proxy_data['url'],
             'proxy_id': proxy_data['id']})

        browser_profile['retry'] = browser_blocked
        if browser_blocked:
            browser_profile['retry_no'] = int(browser_profile.get('retry_no', 0)) + 1
        else:
            browser_profile['retry_no'] = 0

        if not browser_blocked:
            # Add new browser
            self._browsers.append(browser_profile)

    def _is_blocked(self, browser):
        if 'Error 403' in browser['webdriver'].title:
            return True
        browser_blocked = True
        try:
            browser['webdriver'].find_element_by_xpath('//form[@action="CaptchaRedirect"]')
        except NoSuchElementException:
            browser_blocked = False
        return browser_blocked

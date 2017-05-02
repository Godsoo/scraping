# -*- coding: utf-8 -*-
import json
import time
from httplib import HTTPException
from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from product_spiders.phantomjs import PhantomJS
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException


from . import (
    make_product_from_dict,
    filter_color,
    InvalidRecurringChargeForPricePlan,
    filter_duplicates_with_higher_price
)

devices_url = 'https://www.swisscom.ch/en/residential/mobile/devices.html'

ajax_url_form = 'https://www.swisscom.ch/portalshop/en/res/Filter/MobileFilter/RES_MO_PHONES'
ajax_url_res = 'https://www.swisscom.ch/portalshop/en/res/Filter/MobileFilterResult/RES_MO_PHONES'

order_url_template = 'https://www.swisscom.ch/en/res/configuration.html?productid='
configuration_url_template = 'https://www.swisscom.ch/portalshop/en/res/Configuration/Index?productid='


class SwisscomSpider(BaseSpider):
    name = 'orange_swisscom.ch'
    allowed_domains = ['swisscom.ch']
    start_urls = (
        devices_url,
    )

    products_per_page = 100

    products = []

    errors = []

    # account specific fields
    operator = 'Swisscom'
    channel = 'Direct'

    rotate_agent = True

    def _create_browser(self):
        if hasattr(self, '_proxies_list'):
            import random
            proxy = random.choice(self._proxies_list)
            if proxy:
                self.log("[[SWISSCOMCH]] Creating browser with proxy")
                return PhantomJS.create_browser(proxy={'host': proxy})
        self.log("[[SWISSCOMCH]] Creating browser without proxy")
        return PhantomJS.create_browser()

    def _do_browser_action_tries(self, function, tries=10):
        try_number = 1
        while try_number <= tries:
            try:
                function()
            except (TimeoutException, WebDriverException, NoSuchElementException, HTTPException):
                time.sleep(1)
            else:
                return True
        return False

    def _browser_load_page_with_tries(self, url, tries=10):
        return self._do_browser_action_tries(lambda: self._browser.get(url), tries)

    def __init__(self, *a, **kw):
        super(SwisscomSpider, self).__init__(*a, **kw)
        self._browser = None
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        """
        Runs after all pages and items processed but before closing
        Populates all 'out of stock' items as they were just stored in attribute
        """
        self.log("Spider idle")

        if self.products:
            request = Request(self.start_urls[0], dont_filter=True, callback=self.closing_parse)
            self._crawler.engine.crawl(request, self)

    def closing_parse(self, response):
        self.log("Processing items")
        self.products = filter_duplicates_with_higher_price(self.products)
        while self.products:
            yield(self.products.pop())

    def parse(self, response):
        self.log("[[SWISSCOMCH]] Loading devices using PhantomJS")
        self._browser = self._create_browser()
        self._browser_load_page_with_tries(devices_url)

        products = []

        counter = 1
        while True:
            time.sleep(15)
            hxs = HtmlXPathSelector(text=self._browser.page_source)
            total_count = int(hxs.select("//div[@id='scs-filter-productcounter']/text()")
                              .re("(\d*) of \d* products")[0])

            products = hxs.select('//div[contains(@class, "scs-product-grid")]//div[contains(@id, "gridProduct")]')
            self.log("[[SWISSCOMCH]] All products: %d. Loaded products: %d" % (total_count, len(products)))
            # self._browser.save_screenshot('/tmp/temp%d.png' % counter)
            self._browser.set_window_size(
                self._browser.get_window_size()['width'], self._browser.get_window_size()['height'] + 300)

            if len(products) == total_count:
                break

            counter += 1
            if counter > 100:
                self.log("[[SWISSCOMCH]] Error: couldn't load devices using PhantomJS")
                return

        for i, product in enumerate(products):
            device_name = product.select('.//div[@class="scs-filter-productname"]/text()').extract()
            device_name = device_name[0].strip()
            device_name = filter_color(device_name)

            image_url = product.select('.//div[@class="scs-filter-productimage"]//img/@src').extract()
            image_url = urljoin(get_base_url(response), image_url[0])

            device_url = product.select('.//div[@class="scs-filter-productimage"]//a/@href').extract()
            device_url = urljoin(get_base_url(response), device_url[0])

            product_id = product.select('.//@data-product-id').extract()
            product_id = product_id[0]

            product_info = {
                'image_url': image_url,
                'brand': '',
                'device_name': device_name,
                'url': device_url
            }
            meta = {
                'product': product_info,
                'product_id': product_id,
                'product_url': device_url
            }

            self.log("Collected device: %s" % device_name)

            url = meta['product_url']
            r = Request(url, callback=self.parse_product_page, meta=meta, dont_filter=True)
            yield r

    def parse_product_page(self, response):
        hxs = HtmlXPathSelector(response)

        if hxs.select('//div[@class="scs-promotion"]'):
            promotion = True
        else:
            promotion = False

        json_data = json.loads(hxs.select("//*[@data-json]/@data-json").extract()[0])

        for prod_data in json_data['items']:
            product_name = prod_data['name']

            product_info = response.meta['product'].copy()
            product_info['promotion'] = promotion
            product_info['device_name'] = product_name

            for plan in prod_data['subscriptions']:
                plan_name = plan['name']
                if not plan_name:
                    self.log("[[TESTING]] SKIP! No plan name!")
                    continue
                self.log("[[TESTING]] Found plan: %s" % plan_name)

                if not self._check_plan_is_correct(plan_name, response):
                    self.log("[[TESTING]] SKIP! Plan does not fit!")
                    continue

                for duration_data in plan['durationPrices']:
                    period = duration_data['duration']
                    one_time_charge = duration_data['price']
                    per_month = plan['recurringCharge']
                    if not per_month:
                        self.log("[[TESTING]] SKIP! No monthly pay!")
                        continue

                    try:
                        product = self._make_product(response, product_info, plan_name, per_month, period, one_time_charge)
                        self.products.append(product)
                    except InvalidRecurringChargeForPricePlan:
                        self.log("[[TESTING]] SKIP! Invalid recurring charge!")
                        pass

    def _make_product(self, response, product_info, plan_name, per_month, period, one_time_charge):
        return make_product_from_dict(response, product_info, self.operator, self.channel, plan_name, per_month, period, one_time_charge, ignore_rec_charge_diff=True)

    def _check_plan_is_correct(self, plan_name, response):
        if 'M-Budget'.lower() in plan_name.lower():
            self.log("Found M-Budget plan for device: %s" % response.meta['product']['device_name'])
            return False
        else:
            return True

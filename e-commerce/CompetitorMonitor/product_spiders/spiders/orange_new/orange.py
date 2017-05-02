# -*- coding: utf-8 -*-
import time
import re
from urlparse import urljoin
from httplib import HTTPException
from collections import defaultdict

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.exceptions import CloseSpider
from scrapy import log

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from product_spiders.phantomjs import PhantomJS
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

from product_spiders.spiders.orange_new import (
    make_product_from_selector,
    InvalidCategory,
)

# account specific fields
operator = 'Orange'
channel = 'Direct'

devices_url = 'https://shop.salt.ch/en/devices/'
subscriptions_url = 'https://shop.salt.ch/en/plans/'


def _generate_variants(struct):
    if len(struct) < 1:
        return
    main_key = sorted(struct)[0]
    main_values = struct[main_key]
    temp = {}
    for key, values in struct.items():
        if key != main_key:
            temp[key] = values

    for value in main_values:
        if temp:
            for res in _generate_variants(temp):
                res[main_key] = value
                yield res
        else:
            yield {main_key: value}

def generate_variants(priceplan_components):
    temp = {}
    for key in priceplan_components:
        if isinstance(priceplan_components[key], dict):
            values = priceplan_components[key].keys()
            temp[key] = values
        else:
            temp[key] = [priceplan_components[key]]
    variants = _generate_variants(temp)
    return list(variants)


def fix_name(device_name):
    """
    >>> fix_name('S6 32Gb + Beats Solo 2')
    'Galaxy S6 32Gb + Beats Solo 2'
    """
    if device_name == 'M8':
        return 'One M8'
    if device_name == 'M9':
        return 'One M9'

    if 'Galaxy S V'.lower() in device_name.lower():
        regex = 'Galaxy S V'
        return re.sub(regex, 'Galaxy S5', device_name, flags=re.I + re.U)

    if 'S6 32Gb' in device_name:
        return device_name.replace('S6', 'Galaxy S6')

    if 'S6 Edge 32Gb' in device_name:
        return device_name.replace('Edge S6', 'Galaxy S6')

    return device_name


class OrangeSpider(BaseSpider):
    name = 'orange_orange.ch'
    allowed_domains = ['orange.ch', 'salt.ch']
    start_urls = (
        'https://shop.salt.ch/',
    )

    errors = []

    def _create_browser(self):
        if hasattr(self, '_proxies_list'):
            import random
            proxy = random.choice(self._proxies_list)
            if proxy:
                self.log("[[ORANGECH]] Creating browser with proxy")
                return PhantomJS.create_browser(proxy={'host': proxy})
        self.log("[[ORANGECH]] Creating browser without proxy")
        return PhantomJS.create_browser()

    def start_requests(self):
        return []

    def __init__(self, *args, **kwargs):
        super(OrangeSpider, self).__init__(*args, **kwargs)

        dispatcher.connect(self.process_next_step, signals.spider_idle)

        self.current_step = 'START'
        self.finished_step = None

        self.current_period = None

        self.devices = {}
        self.priceplans = {}
        self.priceplans_variants = {}
        self.priceplans_formdata = {}
        self.processed_priceplans = {}

        self._browser = None

        self.csrfmiddlewaretoken = None

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

    def process_next_step(self, spider):
        if not self._finished():
            self.log("[[ORANGECH]] Processing next step")
            r = Request(self.start_urls[0],
                        callback=self.crawl_next,
                        errback=lambda error: self.crawl_next(None),
                        dont_filter=True,
                        meta={'dont_merge_cookies': True, 'dont_redirect': True})
            self._crawler.engine.crawl(r, self)

    def _finished(self):
        if self.current_step == 'START' and self.finished_step is None:
            return False
        elif self.current_step == 'COLLECT_DEVICES' and self.finished_step == 'START':
            return False
        elif self.current_step == 'PROCESS_PLANS' and self.finished_step == 'COLLECT_DEVICES':
            return False
        elif self.current_step == 'PROCESS_PLANS_DEVICES' and self.finished_step == 'PROCESS_PLANS':
            return False
        return True

    def crawl_next(self, response):
        if self._browser is None:
            self._browser = self._create_browser()
        if self.current_step == 'START' and self.finished_step is None:
            self.finished_step = 'START'
            self.log("[[ORANGECH]] Collecting devices")
            r = Request(devices_url, callback=self.parse_device_list_initial, dont_filter=True)
            yield r
        elif self.current_step == 'COLLECT_DEVICES' and self.finished_step == 'START':
            self.finished_step = 'COLLECT_DEVICES'
            self.log("[[ORANGECH]] Collected devices: %d" % len(self.devices))
            self.log("[[ORANGECH]] Processing price plan configurations")
            r = Request(subscriptions_url, callback=self.parse_subscriptions_group_variants, dont_filter=True)
            yield r
        elif self.current_step == 'PROCESS_PLANS' and self.finished_step == 'COLLECT_DEVICES':
            self.finished_step = 'PROCESS_PLANS'
            self.log("[[ORANGECH]] Price plan configurations collected")
            self.log("[[ORANGECH]] Collecting device prices")
            r = Request(subscriptions_url, callback=self.parse_subscriptions_period_variants, dont_filter=True)
            yield r
        elif self.current_step == 'PROCESS_PLANS_DEVICES' and self.finished_step == 'PROCESS_PLANS':
            self.finished_step = 'PROCESS_PLANS_DEVICES'
            self.log("[[ORANGECH]] Finished")
            self._browser.quit()
        else:
            self.log("[[ORANGECH]] SPIDER ERROR: Undefined step: %s, finished step: %s" % (self.current_step, self.finished_step), log.ERROR)

    def parse_device_list_initial(self, response):
        self.current_step = 'COLLECT_DEVICES'

        hxs = HtmlXPathSelector(response)

        for i, el in enumerate(hxs.select("//div[@data-product-grid]/div[contains(@class, 'product-item')]")):
            link = el.select(".//a[contains(@class, 'btn-detail')]/@href").extract()
            if not link:
                continue
            # skip SIM-only
            if el.select(".//div[@class='product-overflow']/h2/text()").re("(?i)sim only"):
                continue
            link = link.pop()
            link = urljoin(get_base_url(response), link)
            device_id = el.select("@id").extract()[0]
            r = Request(link, callback=self.parse_device_page, meta={'device_id': device_id})
            yield r

    def parse_device_page(self, response):
        self.log("[[TESTING]] Scraping device from: %s" % response.url)
        hxs = HtmlXPathSelector(response)

        device_name = "".join(hxs.select("//div[@class='product-detail']//h1/text()").extract())
        device_name = device_name.partition("- Delivered")[0].strip()
        device_name = re.sub('is out of stock - sorry', '', device_name, flags=re.I).strip()

        device_name = fix_name(device_name)

        url = response.url
        brand = re.search('.*/en/devices/([^/]*)/', url).group(1).title()
        image_url = hxs.select("//div[@class='product-image-big']//img/@src").extract()[0]
        if image_url:
            image_url = urljoin(get_base_url(response), image_url[0])
        else:
            image_url = None

        network_gen = '4G'

        device_id = response.meta['device_id']

        self.log("[[ORANGECH]] Collected device. Id: %s, name: %s" % (device_id, device_name))

        self.devices[device_id] = {
            'id': device_id,
            'name': device_name,
            'brand': brand,
            'url': url,
            'image_url': image_url,
            'network_gen': network_gen
        }

    def parse_subscriptions_group_variants(self, response):
        self.current_step = 'PROCESS_PLANS'

        hxs = HtmlXPathSelector(response)

        self.csrfmiddlewaretoken = hxs.select("//form[@id='buy-now-form']//input[@name='csrfmiddlewaretoken']/@value").extract()[0]

        if not self._browser_load_page_with_tries(response.url):
            self.errors.append("Failed to load page with PhantomJS: %s" % response.url)
            raise CloseSpider("Failed to load page with PhantomJS: %s" % response.url)

        time.sleep(30)

        should_continue = True

        while should_continue:
            should_continue = False
            drop_down_el = self._browser.find_element_by_xpath("//form[@id='form_subscription_choice']//a[@class='select2-choice']")
            self._do_browser_action_tries(drop_down_el.click)
            for plan in self._browser.find_elements_by_xpath("//ul[@id='select2-results-4']/li"):
                plan_name = plan.text
                if plan_name.lower() == 'prepay':
                    continue
                if plan_name not in self.priceplans:
                    self.log("[[ORANGECH]] Scraping price plans: %s" % plan_name)
                    plan = self._browser.find_element_by_xpath("//ul[@id='select2-results-4']/li[div[contains(text(), '%s')]]" % plan_name)
                    self._do_browser_action_tries(plan.click)

                    hxs2 = HtmlXPathSelector(text=self._browser.page_source)
                    self._scrape_subscriptions_data(hxs2, plan_name_base=plan_name)

                    should_continue = True

                    break

    def _scrape_subscriptions_data(self, hxs, plan_name_base):
        form = hxs.select("//form[@id='subscription-packages-form']")

        if plan_name_base not in self.priceplans or not self.priceplans[plan_name_base]:
            priceplan_components = defaultdict()
            for section in form.select("div[@class='row']"):
                section_id = section.select("@id").extract()[0].replace('subscription-', '')
                group_name = 'group-%s' % section_id
                priceplan_components[group_name] = {}
                blocks = section.select(".//ul[@class='subscriptions-options']/li[.//input[@name='%s']]" % group_name)
                for block in blocks:
                    input = block.select(".//input[@name='%s']" % group_name)
                    value = input.select("@value").extract()[0]

                    name = block.select(".//h5[@class='subscriptions-options-cell-title']/text()").extract()[0]
                    price = block.select(".//h5[@class='subscriptions-options-cell-price']/text()").extract()[0]\
                        .replace("CHF ", "").replace(".-", "")
                    if "instead" in price:
                        price = price.split("instead")[0].strip()

                    priceplan_components[group_name][value] = {
                        'name': name,
                        'price': price
                    }
                if not blocks:
                    rows = section.select('.//div[@class="row"]')
                    for row in rows:
                        plan_name = row.select(".//h4/text()").extract()[0].strip()
                        options = row.select(".//div[@class='vertical-option-select']")
                        options += row.select(".//div[@class='vertical-option-select selected']")
                        for option in options:
                            option_name = option.select(".//h5/text()").extract()[0].strip()
                            if 'salt pack' == option_name.lower():
                                option_name = plan_name + ' ' + option_name
                            input = option.select('.//input')
                            value = input.select("@value").extract()[0]
                            price = option.select('.//span[contains(@class, "select-price")]/text()').extract()[0]\
                                .replace(".-", "")
                            priceplan_components[group_name][value] = {
                                'name': option_name,
                                'price': price
                            }
            self.log("[[TESTING]] Price plan components")
            self.log("[[TESTING]] %s" % str(priceplan_components))
            self.priceplans[plan_name_base] = priceplan_components

            variants = generate_variants(priceplan_components)

            self.priceplans_variants[plan_name_base] = variants

    def parse_subscriptions_period_variants(self, response):
        if len(self.devices) < 1:
            self.log("[[ORANGECH]] No devices collected on previous steps. Stopping!")
            return
        self.current_step = 'PROCESS_PLANS_DEVICES'

        if not self._browser_load_page_with_tries(devices_url):
            self.errors.append("Failed to load page with PhantomJS: %s" % devices_url)
            raise CloseSpider("Failed to load page with PhantomJS: %s" % devices_url)

        # reset to SIM-only
        time.sleep(30)
        el = self._browser.find_element_by_xpath("//div[@class='product-item'][not(@id)]//button[contains(text(), 'Select')]")
        self._do_browser_action_tries(el.click)
        time.sleep(30)

        if not self._browser_load_page_with_tries(response.url):
            self.errors.append("Failed to load page with PhantomJS: %s" % response.url)
            raise CloseSpider("Failed to load page with PhantomJS: %s" % response.url)

        for self.current_period in ['12', '24']:

            if self.current_period not in self.processed_priceplans:
                self.processed_priceplans[self.current_period] = {}

            if len(self.priceplans) < 1:
                return

            self.log('[[ORANGECH]] Processing period: %s months' % self.current_period)

            drop_down_el = self._browser.find_element_by_xpath("//form[@id='form_subscription_length']//a[@class='select2-choice']")
            self._do_browser_action_tries(drop_down_el.click)
            el = self._browser.find_element_by_xpath("//ul[@id='select2-results-6']/li/div[contains(text(), '%s')]" % self.current_period)
            self._do_browser_action_tries(el.click)

            for plan_name_base in sorted(self.priceplans):
                # plan_formdata = self.priceplans_formdata[plan_name_base]
                self.log('[[ORANGECH]] Processing base price plan %s with period %s months' % (plan_name_base, self.current_period))
                drop_down_el = self._browser.find_element_by_xpath("//form[@id='form_subscription_choice']//a[@class='select2-choice']")
                self._do_browser_action_tries(drop_down_el.click)
                el = self._browser.find_element_by_xpath("//ul[@id='select2-results-4']/li/div[contains(text(), '%s')]" % plan_name_base)
                self._do_browser_action_tries(el.click)

                if plan_name_base not in self.processed_priceplans[self.current_period]:
                    self.processed_priceplans[self.current_period][plan_name_base] = set()

                for i, variant in enumerate(sorted(self.priceplans_variants[plan_name_base])):
                    grouped_key = ";".join(["%s:%s" % (key, variant[key]) for key in sorted(variant.keys())])

                    if grouped_key in self.processed_priceplans[self.current_period][plan_name_base]:
                        continue

                    if 'young' in plan_name_base.lower():
                        plan_name = plan_name_base[:]
                        for key, value in variant.items():
                            if 'Young' in self.priceplans[plan_name_base][key][value]['name']:
                                plan_name = plan_name + ' ' + self.priceplans[plan_name_base][key][value]['name'].replace("Orange Young", "").replace("Young", "").strip()
                        for key, value in variant.items():
                            if 'Young' not in self.priceplans[plan_name_base][key][value]['name']:
                                plan_name = plan_name + ', ' + self.priceplans[plan_name_base][key][value]['name']
                    else:
                        plan_name = plan_name_base + " " + ", ".join([self.priceplans[plan_name_base][key][variant[key]]['name'] for key in sorted(variant.keys())])

                    price = sum([int(self.priceplans[plan_name_base][key][variant[key]]['price']) for key in variant.keys()])

                    meta = {
                        'plan_name_base': plan_name_base,
                        'grouped_key': grouped_key,
                        'plan_name': plan_name,
                        'per_month': price
                    }

                    self.log('[[ORANGECH]] Selecting price plan %s with period %s months' % (plan_name, self.current_period))

                    for key, value in variant.items():
                        el = self._browser.find_element_by_xpath("//input[@name='%s'][@value='%s']" % (key, value))
                        self._do_browser_action_tries(el.click)
                        time.sleep(5)

                    self.log('[[ORANGECH]] Clicking period again: %s months' % self.current_period)
                    el = self._browser.find_element_by_xpath("//select[@name='contract_length']/option[@value='%s']" % self.current_period)
                    if not el.is_selected():
                        self._do_browser_action_tries(el.click)
                        time.sleep(5)

                    self.log('[[ORANGECH]] Loading device prices for price plan: %s, %s months' % (plan_name, self.current_period))
                    # time.sleep(30)

                    if not self._browser_load_page_with_tries(devices_url):
                        self.errors.append("Failed to load page with PhantomJS: %s" % devices_url)
                        raise CloseSpider("Failed to load page with PhantomJS: %s" % devices_url)
                    hxs = HtmlXPathSelector(text=self._browser.page_source)

                    for item in self.parse_device_prices_for_priceplan(hxs, meta):
                        yield item

                    self.processed_priceplans[self.current_period][plan_name_base].add(grouped_key)

                    if not self._browser_load_page_with_tries(subscriptions_url):
                        self.errors.append("Failed to load page with PhantomJS: %s" % subscriptions_url)
                        raise CloseSpider("Failed to load page with PhantomJS: %s" % subscriptions_url)

    def parse_device_prices_for_priceplan(self, hxs, meta):
        plan_name = meta['plan_name']
        per_month = meta['per_month']
        period = self.current_period

        processed_device_ids = []
        processed_devices = []

        devices = hxs.select("//div[@data-product-grid]/div[contains(@class, 'product-item')]")

        for i, el in enumerate(devices):
            link = el.select(".//a[contains(@class, 'btn-detail')]/@href").extract()
            if not link:
                continue

            # skip no-SIM
            if el.select(".//div[@class='product-overflow']/h2/text()").re("(?i)sim only"):
                continue

            device_id = el.select("@id").extract()[0]
            if device_id not in self.devices:
                self.log("[[ORANGECH]] Device id not in the list: %s. Index: %d" % (device_id, i))
                continue

            device_data = self.devices[device_id]

            price = el.select(".//div[@data-one-time-fee]//p[@class='product-price']/text()").extract()
            if not price:
                self.log("[[ORANGECH]] No price for device %s in price plan %s and period %s" % (
                    device_data['name'],
                    plan_name,
                    period
                ))
                continue

            price = price.pop().replace('CHF ', '').replace('.-', '')

            product_info = {
                'device_name': device_data['name'],
                'network_gen': device_data['network_gen'],
                'brand': device_data['brand'],
                'image_url': device_data['image_url'],
                'url': device_data['url']
            }

            try:
                processed_devices.append(self._make_product(hxs, product_info, plan_name, per_month, period, price))
            except InvalidCategory:
                pass
            else:
                processed_device_ids.append(device_id)

        for device_id in self.devices:
            if device_id not in processed_device_ids:
                self.log('[[ORANGECH]] Error: device "%s" not found for price plan %s and period %s' % (
                    self.devices[device_id]['name'],
                    plan_name,
                    period
                ))
        for device in processed_devices:
            yield device

    def _make_product(self, hxs, product_info, plan_name, per_month, period, one_time_charge):
        if ' and Zattoo' in plan_name:
            plan_name = plan_name.replace(' and Zattoo', '').strip()
        return make_product_from_selector(hxs, product_info, operator, channel, plan_name, per_month, period, one_time_charge, ignore_rec_charge_diff=True)

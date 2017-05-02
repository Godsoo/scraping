# -*- coding: utf-8 -*-
import time
import urllib
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.contrib.spidermiddleware.httperror import HttpError

from product_spiders.utils import url_quote

from product_spiders.spiders.orange_new import (
    make_product_from_response,
    filter_color,
    InvalidCategory,
    filter_duplicates_with_higher_price,
    get_category_by_recurring_charge,
    get_priceplans_for_category,
    check_price_plan_exists
)

# account specific fields
channel = 'MobileZone'

def js_timestamp():
    return int(time.time() * 1000)

class MobilezoneSpider(BaseSpider):
    name = 'orange_mobilezone.ch'
    allowed_domains = ['mobilezone.ch']
    start_urls = (
        'http://www.mobilezone.ch/mobiltelefone',
    )

    ajax_plans_url = 'http://www.mobilezone.ch/mobiltelefone/extras/?extras_tab=offers_new'

    products = []

    def __init__(self, *a, **kw):
        super(MobilezoneSpider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.pages_reqs = []
        self.products_reqs = []
        self.priceplans_reqs = []

        self.errors = []

    def spider_idle(self, spider):
        """
        Runs after all pages and items processed but before closing
        Populates all 'out of stock' items as they were just stored in attribute
        """
        self.log("[[MOBILEZONE]] Spider idle")

        if self.priceplans_reqs:
            req = self.priceplans_reqs.pop()
        elif self.products_reqs:
            req = self.products_reqs.pop()
        elif self.pages_reqs:
            req = self.pages_reqs.pop()
        else:
            req = None

        self.log("[[MOBILEZONE]] Number of requests left: %d" % (len(self.priceplans_reqs) + len(self.products_reqs) + len(self.pages_reqs), ))
        self.log("[[MOBILEZONE]] Priceplans requests: %d" % len(self.priceplans_reqs))
        self.log("[[MOBILEZONE]] Products requests: %d" % len(self.products_reqs))
        self.log("[[MOBILEZONE]] Pages requests: %d" % len(self.pages_reqs))

        if req:
            self.log("[[MOBILEZONE]] Still have requests. Launching")
            self._crawler.engine.crawl(req, self)
        elif self.products:
            self.log("[[MOBILEZONE]] Collecting products")
            request = Request(self.start_urls[0], dont_filter=True, callback=self.closing_parse)
            self._crawler.engine.crawl(request, self)
        else:
            self.log("[[MOBILEZONE]] No requests and no products")

    def closing_parse(self, response):
        self.log("[[MOBILEZONE]] Processing items")
        self.products = filter_duplicates_with_higher_price(self.products)
        while self.products:
            yield(self.products.pop())

    def _invoke_next_req(self):
        if self.priceplans_reqs:
            req = self.priceplans_reqs.pop()
        elif self.products_reqs:
            req = self.products_reqs.pop()
        elif self.pages_reqs:
            req = self.pages_reqs.pop()
        else:
            return None
        return req

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        per_page = 10
        products_count = int(hxs.select('//div[@class="total"]/text()').re(r'\d+')[0])

        self.log("[[MOBILEZONE]] Found %d products overall" % products_count)

        for i in xrange(0, products_count, per_page):
            data = {'range': '%d,%d' % (i, per_page), '_': js_timestamp()}
            url = 'http://www.mobilezone.ch/mobiltelefone'
            headers = {'X-Requested-With': 'XMLHttpRequest'}
            req = Request(
                url + '?' + urllib.urlencode(data),
                headers=headers,
                callback=self.parse_products,
                errback=lambda failure: self.process_products_list_url_error(failure,
                                                                             url + '?' + urllib.urlencode(data),
                                                                             headers,
                                                                             self.parse_products,
                                                                             retry_count=10),
                meta={'start': i}
            )
            self.pages_reqs.append(req)

        # invoke next page
        yield self._invoke_next_req()

    def __add_request_retry(self, failure, url, headers, callback, errback, req_list, retry_count):
        retried = False
        if failure.type is HttpError:
            if retry_count > 0:
                req = Request(
                    url,
                    headers=headers,
                    callback=callback,
                    dont_filter=True,
                    errback=lambda failure: errback(failure,
                                                    url,
                                                    headers,
                                                    callback,
                                                    retry_count=retry_count - 1)
                )
                req_list.append(req)
                retried = True

        if not retried:
            yield self._invoke_next_req()

    def process_products_list_url_error(self, failure, url, headers, callback, retry_count=10):
        self.__add_request_retry(failure, url, headers, callback, self.process_products_list_url_error, self.pages_reqs, retry_count)

    def process_product_url_error(self, failure, url, headers, callback, retry_count=10):
        self.__add_request_retry(failure, url, headers, callback, self.process_product_url_error, self.products_reqs, retry_count)

    def parse_error(self, failure):
        yield self._invoke_next_req()

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('.//div[contains(@class, "mobile-grid article")]')
        self.log("[[MOBILEZONE]] Parsing products. Page start: %s. Found product elements: %d" %
                 (response.meta['start'], len(products)))
        for i, product in enumerate(products):
            device_name = product.select('div[@class="data"]/h3/a/text()').extract()[0]
            self.log("[[MOBILEZONE]] Found device: %s" % device_name)

            image_url = product.select('div[@class="overview-product-image"]//img/@src').extract()
            if image_url:
                image_url = urljoin(get_base_url(response), image_url[0])
            else:
                image_url = ''
            url = product.select('div[@class="data"]/h3/a/@href').extract()[0]
            url = urljoin(get_base_url(response), url)
            meta = {
                'image_url': image_url,
                'product_url': url
            }
            req = Request(url, callback=self.parse_product_spec, meta=meta, dont_filter=True,
                          errback=lambda failure: self.process_product_url_error(failure,
                                                                                 url,
                                                                                 {},
                                                                                 self.parse_product_spec,
                                                                                 retry_count=10))
            self.products_reqs.append(req)

        # invoke next product
        yield self._invoke_next_req()

    def parse_product_spec(self, response):
        if response.status == 500:
            yield self._invoke_next_req()
            return

        meta = response.meta

        yield Request(meta['product_url'], meta=meta, callback=self.parse_product, dont_filter=True,
                      errback=lambda failure: self.process_product_url_error(failure,
                                                                             response.meta['product_url'],
                                                                             {},
                                                                             self.parse_product_spec,
                                                                             retry_count=10))

    def parse_product(self, response):
        if response.status == 500:
            yield self._invoke_next_req()
            return
        hxs = HtmlXPathSelector(response)

        device_name = hxs.select('//div[@id="details"]/h1//text()').extract()[0].strip()
        device_name = filter_color(device_name)

        brand = ''

        url = response.url

        image_url = response.meta['image_url']

        in_stock = False
        for i, el in enumerate(hxs.select('//div[@id="data"]/div[contains(@class, "availability")]/span')):
            if el.select('@class').extract()[0] == 'avail-box-green':
                in_stock = True
                break
            else:
                if el.select('@class').extract()[0] != 'avail-box-black' and i > 0:
                    in_stock = True
                    break

        product_info = {
            'device_name': device_name,
            'brand': brand,
            'url': url,
            'image_url': image_url,
            'in_stock': in_stock,
        }

        response.meta['product'] = product_info

        req = Request(
            self.ajax_plans_url,
            callback=self.parse_plans,
            meta={'product': product_info},
            dont_filter=True,
            errback=lambda failure: self.process_product_url_error(failure,
                                                                   response.meta['product_url'],
                                                                   {},
                                                                   self.parse_product_spec,
                                                                   retry_count=10)
        )
        yield req

    def parse_plans(self, response):
        hxs = HtmlXPathSelector(response)

        products = []
        providers_count = len(hxs.select('//div[@class="provider"]'))
        for provider in hxs.select('//div[@class="provider"]'):
            operator = provider.select('preceding-sibling::h3')[-1].select('a/text()').re(r'(.*) Angebote')[0]
            plans = {}
            for plan in provider.select('.//div[@class="content hidden"]'):
                plan_name = plan.select('h2/text()').extract()[0].strip()
                per_month = plan.select(u'.//tr/td[text()="Monatsgebühr"]/following-sibling::td/text()').re('[\d.]+')[0]
                plans[plan_name.lower()] = per_month

            for plan in provider.select('.//table[contains(@class, "provider_table")]/tr[@class="content"]'):
                plan_name = plan.select('td[@class="name"]/text()').extract()[0].strip()
                per_month = plans[plan_name.lower()]

                # if not check_price_plan_exists(operator, plan_name, per_month):
                #     category = get_category_by_recurring_charge(per_month)
                #     priceplans = get_priceplans_for_category(category, operator)

                # else:
                priceplans = [
                    {'price plan': plan_name, 'recurring charge': per_month}
                ]

                period = '12 Months'
                one_time_charge = plan.select('td[@class="price"][1]/label/text()').re("[\d.]+")
                if one_time_charge:
                    for row in priceplans:
                        plan_name = row['price plan']
                        per_month = row['recurring charge']
                        product_info = (operator, plan_name, per_month, period, one_time_charge[0])
                        products.append(product_info)

                period = '24 Months'
                one_time_charge = plan.select('td[@class="price"][2]/label/text()').re("[\d.]+")
                if one_time_charge:
                    for row in priceplans:
                        plan_name = row['price plan']
                        per_month = row['recurring charge']
                        product_info = (operator, plan_name, per_month, period, one_time_charge[0])
                        products.append(product_info)

        count = 0
        self.log("[[MOBILEZONE]] Non-Orange product infos found: %d" % len(products))
        for product_info in products:
            operator, plan_name, per_month, period, one_time_charge = product_info
            try:
                if providers_count > 1:
                    # strip operator from product name
                    product = self._make_product(response, operator, plan_name, per_month, period, one_time_charge, strip_operator=True)
                else:
                    product = self._make_product(response, operator, plan_name, per_month, period, one_time_charge)
                self.log("[[MOBILEZONE]] Collecting product: %s" % product['identifier'])
                self.products.append(product)
                count += 1
            except InvalidCategory:
                self.log("[[MOBILEZONE]] Exception")
                pass
        self.log("[[MOBILEZONE]] Non-Orange product infos added: %d" % count)

        # process Orange

        offers_url = hxs.select("//form[contains(@action, 'offer_configurators')]/@action").re(r'.*offer_configurators$')
        if not offers_url:
            self.log("[ERROR] Could not find offers url for orange plan on price plan page: %s" % response.url)
            yield self._invoke_next_req()
            return

        offers_url = urljoin(get_base_url(response), offers_url[0])

        offers_url2 = offers_url.replace('offer_configurators', 'offer_configurators/3')

        authenticity_token = hxs.select("//input[@name='authenticity_token']/@value").extract()[0]

        for period in ["12", "24"]:
            for talk_text in hxs.select("//li[not(contains(@data-class, 'young'))]/input[@name='categories[talk-text]']"):
                talk_text_id = talk_text.select("@id").extract()[0]
                talk_text_name = hxs.select("//label[@for='%s']/text()" % talk_text_id).extract()[0]
                talk_text_value = talk_text.select("@value").extract()[0]

                for surf in hxs.select("//li[not(contains(@data-class, 'young'))]/input[@name='categories[surf]']"):
                    surf_id = surf.select("@id").extract()[0]
                    surf_name = hxs.select("//label[@for='%s']/text()" % surf_id).extract()[0]
                    surf_value = surf.select("@value").extract()[0]

                    for care_el in hxs.select("//li[not(contains(@data-class, 'young'))]/input[@name='categories[care]']"):
                        care_id = care_el.select("@id").extract()[0]
                        care_name = hxs.select("//label[@for='%s']/text()" % care_id).extract()[0]
                        care_value = care_el.select("@value").extract()[0]

                        plan_name = "Me %s / %s / %s" % (talk_text_name, surf_name, care_name)

                        request_body = [
                            ('_method', 'put'),
                            ('authenticity_token', authenticity_token),
                            ('offer_configurator[period]', period),
                            ('offer_configurator[category_ids]', '%s,+%s,+%s' % (
                                talk_text_value,
                                surf_value,
                                care_value
                            )),
                            ('offer_configurator[hybrid]', '0'),
                            ('tab', 'orange_me')
                        ]
                        request_body = ["=".join(map(url_quote, x)) for x in request_body]
                        request_body = "&".join(request_body)

                        headers = {
                            "Accept": "text/javascript, application/javascript, */*",
                            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                            "X-Requested-With": "XMLHttpRequest"
                        }

                        r = Request(
                            url=offers_url2,
                            method='POST',
                            body=request_body,
                            meta={
                                'dont_retry': True,
                                'product': response.meta['product'],
                                'period': period,
                                'plan_name': plan_name,
                                'operator': 'Orange'
                            },
                            callback=self.parse_offer_plan,
                            errback=self.parse_offer_plan_error,
                            headers=headers
                        )
                        self.priceplans_reqs.append(r)

            plan_els = hxs.select("//li[contains(@data-class, 'young')]/input[@name='categories[talk-text]']")
            plan_els += hxs.select("//li[contains(@data-class, 'natel')]/input[@name='categories[swisscom-infinity]']")
            plan_els += hxs.select("//li[contains(@data-class, 'natel')]/input[@name='categories[swisscom-entry]']")
            plan_els += hxs.select("//li[contains(@data-class, 'natel')]/input[@name='categories[fur-alle-unter-26]']")

            tab_name_map = {
                'talk-text': 'orange_young'
            }
            operator_map = {
                'talk-text': 'Orange',
                'swisscom-infinity': 'Swisscom',
                'swisscom-entry': 'Swisscom',
                'fur-alle-unter-26': 'Swisscom'
            }

            for plan_el in plan_els:
                plan_id = plan_el.select("@id").extract()[0]
                plan_name = hxs.select("//label[@for='%s']/text()" % plan_id).extract()[0]
                category_value = plan_el.select("@value").extract()[0]

                tab = plan_el.select('@name').re('categories\[(.*)\]')[0]
                operator = operator_map[tab]
                if tab in tab_name_map:
                    tab = tab_name_map[tab]
                self.log("[[TESTING]] Plan: %s. Tab: %s. Category value: %s" % (plan_name, tab, category_value))

                request_body = [
                    ('_method', 'put'),
                    ('authenticity_token', authenticity_token),
                    ('offer_configurator[period]', period),
                    ('offer_configurator[category_ids]', category_value),
                    ('offer_configurator[hybrid]', '0'),
                    ('tab', tab)
                ]
                request_body = ["=".join(map(url_quote, x)) for x in request_body]
                request_body = "&".join(request_body)

                headers = {
                    "Accept": "text/javascript, application/javascript, */*",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest"
                }

                r = Request(
                    url=offers_url2,
                    method='POST',
                    body=request_body,
                    meta={
                        'dont_retry': True,
                        'product': response.meta['product'],
                        'period': period,
                        'plan_name': plan_name,
                        'operator': operator
                    },
                    callback=self.parse_offer_plan,
                    errback=self.parse_offer_plan_error,
                    headers=headers
                )
                self.priceplans_reqs.append(r)

        yield self._invoke_next_req()

    def parse_offer_plan(self, response):
        operator = response.meta.get('operator')

        regex = r'\(\'\.offer-result\'\).html\("(.*)"\);\s*copyOfferDescriptionBlock'
        m = re.search(regex, response.body, re.DOTALL)
        if not m:
            regex = r'\(\'\.offer-result\'\).html\("(.*)"\);\s*attachFormElementBehaviour'
        m = re.search(regex, response.body, re.DOTALL)
        if not m:
            msg = 'Error when getting data for price plan: %s. Could not find data in response' % response.meta['plan_name']
            self.log('[ERROR] %s' % msg)
            self.errors.append(msg)
            self.log("[[TESTING]] Body: %s" % response.body)
            return
        body = m.group(1)
        body = body.replace("\\n", " ").replace("\\/", "/").replace('\\"', '"')

        hxs = HtmlXPathSelector(text=body)

        per_month = hxs.select(u"//div[@class='group'][b[contains(text(), 'Monatsgeb')]]/text()").re(r'CHF\s*(\d*\.*\d*)')
        if not per_month:
            msg = 'Error when getting data for price plan: %s. No "per month" value' % response.meta['plan_name']
            self.log('[ERROR] %s' % msg)
            self.errors.append(msg)
            return
        per_month = per_month[0]

        one_time_charge = hxs.select("//div[@class='offer-row'][1]/div[@class='price']/text()").extract()
        if not per_month:
            msg = 'Error when getting data for price plan: %s. No "one time charge" value' % response.meta['plan_name']
            self.log('[ERROR] %s' % msg)
            self.errors.append(msg)
            return
        one_time_charge = one_time_charge[0]

        plan_name = response.meta['plan_name']

        period = response.meta['period']

        try:
            product = self._make_product(response, operator, plan_name, per_month, period, one_time_charge, strip_operator=True)
            self.log("[[MOBILEZONE]] Collecting product: %s" % product['identifier'])
            self.products.append(product)
        except InvalidCategory:
            pass

        yield self._invoke_next_req()

    def parse_offer_plan_error(self, failure):
        from scrapy.contrib.spidermiddleware.httperror import HttpError
        if isinstance(failure.value, HttpError):
            response = failure.value.response

            msg = "Error when downloading data for price plan %s: %s. HTTP status code: %s" % (response.meta.get('plan_name'), str(failure.value), response.status)
            self.log('[ERROR] %s' % msg)
            self.errors.append(msg)

    def _make_product(self, response, operator, plan_name, per_month, period, one_time_charge, strip_operator=False):
        return make_product_from_response(response, operator, channel, plan_name, per_month, period, one_time_charge, strip_operator, ignore_rec_charge_diff=True)

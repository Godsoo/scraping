"""
Base Spider for evanscycles.com

Original Developer: Emiliano M. Rudenick <emr.frei@gmail.com>

IMPORTANT!!

- This website is blocked, please be careful
- This Base Spider uses a custom BSM which works as follow:
  1. Get matched products (only main product data, not options) for websites in `simple_run_websites` attribute
  2. Get previous crawl metadata and load extra data from there
  3. Get all products options for each matched product by using a website AJAX call for this purpose
  4. Copy the rest of data from previous full run crawl results

"""

import os
import csv
import json
import shutil
from extruct.w3cmicrodata import MicrodataExtractor
from datetime import datetime

try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider

from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter, url_query_parameter
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price, get_file_modification_date
from product_spiders.config import new_system_api_roots as API_ROOTS
from product_spiders.config import api_key as API_KEY
from product_spiders.contrib.compmon2 import Compmon2API
from product_spiders.config import DATA_DIR

from scrapy.item import Item, Field


class EvansMeta(Item):
    rrp = Field()


class EvansCyclesBaseSpider(BaseSpider):
    name = 'evanscycles.com'
    allowed_domains = ['evanscycles.com']
    start_urls = ['http://www.evanscycles.com/']

    additional_cookies = {'currency': 'GBP', 'delivery_country': 'GB'}
    location_settings = {'currencyIsoCode': 'GBP', 'countryIsoCode': 'GB'}
    extract_rrp = False
    home_url = 'http://www.evanscycles.com/'
    country = 'GB'
    max_retry = 10
    secondary = False
    full_run_day = 2
    simple_run_websites = [964, 1338, 1486, 484947, 1534]

    AJAX_URL = 'https://www.evanscycles.com/product-listing/getStockAvailability/%s'
    FIELDNAMES = [
        'identifier', 'sku',
        'name', 'price', 'url',
        'category', 'brand', 'image_url',
        'stock', 'rrp',
    ]

    def __init__(self, *args, **kwargs):
        super(EvansCyclesBaseSpider, self).__init__(*args, **kwargs)

        self._products = []
        self._products_file = os.path.join(DATA_DIR, 'evanscycles_base_last_products.csv')
        self._products_file_bak = self._products_file + '.bak'

        self._full_run = datetime.today().weekday() == self.full_run_day
        self.main_products = {}
        self.copy_done = False

        dispatcher.connect(self.spider_closed, signals.spider_closed)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, *args, **kwargs):
        if (not self.secondary) and (not self._full_run) and (not self.copy_done):
            self.copy_done = True
            req = Request('http://www.evanscycles.com/',
                          meta={'dont_redirect': True,
                                'handle_httpstatus_all': True,
                                'ignore_matches': True,
                                'dont_retry': True},
                          callback=self.parse_secondary,
                          dont_filter=True)
            self.crawler.engine.crawl(req, self)

    def spider_closed(self, *args, **kwargs):
        if not self.secondary:
            if os.path.exists(self._products_file):
                copy_file = True
                if os.path.exists(self._products_file_bak):
                    mod_date = get_file_modification_date(self._products_file_bak).date()
                    today_date = datetime.today().date()
                    if mod_date == today_date:
                        copy_file = False
                if copy_file:
                    shutil.copy(self._products_file, self._products_file_bak)
            with open(self._products_file, 'w') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()
                for product in self._products:
                    new_product = {}
                    for k, v in product.items():
                        if k not in self.FIELDNAMES:
                            continue
                        if isinstance(v, unicode):
                            v = v.encode('utf-8')
                        new_product[k] = v
                    writer.writerow(new_product)

    def start_requests(self):
        if self.secondary:
            yield Request('http://www.evanscycles.com/',
                          meta={'dont_redirect': True,
                                'handle_httpstatus_all': True},
                          callback=self.parse_secondary)
        else:
            yield Request('http://www.evanscycles.com/',
                          callback=self.set_location)

    def parse_secondary(self, response):
        self.log('EvansCycles Base Spider >> COPY DATA')
        products_extra = {}
        if (not self.secondary) and hasattr(self, 'prev_crawl_id'):
            products_extra = self._load_extra_data()
            products_filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
        else:
            products_filename = self._products_file

        if os.path.exists(products_filename):
            with open(products_filename) as f:
                reader = csv.DictReader(f)
                for product in reader:
                    new_product = {}
                    for k, v in product.items():
                        if isinstance(v, str):
                            v = v.decode('utf-8')
                        new_product[k] = v


                    if response.meta.get('ignore_matches', False):
                        if product['sku'] in self.main_products:
                            continue

                    loader = ProductLoader(item=Product(), response=response)
                    for field in self.FIELDNAMES:
                        if field != 'rrp':
                            value = new_product[field]
                            if field == 'stock':
                                try:
                                    value = int(value)
                                except ValueError:
                                    continue
                            loader.add_value(field, value)

                    item = loader.load_item()

                    if self.extract_rrp:
                        rrp = ''
                        if 'rrp' in new_product:
                            rrp = str(extract_price(new_product['rrp'])) if new_product['rrp'] else ''
                        else:
                            extra_data = {}
                            if product['sku'] in products_extra:
                                extra_data = products_extra[product['sku']]
                                rrp = extra_data.get('rrp', '')
                            product_copy = dict(product)
                            product_copy['rrp'] = rrp
                            self._products.append(product_copy)
                        metadata = EvansMeta()
                        metadata['rrp'] = rrp
                        item['metadata'] = metadata

                    yield item

    def set_location(self, response):
        callback = self.parse if self._full_run else self.parse_simple
        form_xpath = '//form[@id="country-and-currency-form"]'
        if hasattr(response, 'xpath') and bool(response.xpath(form_xpath)):
            req = FormRequest.from_response(response,
                                            formdata=self.location_settings,
                                            formxpath=form_xpath,
                                            meta={'dont_cache': True},
                                            dont_filter=True,
                                            callback=callback)
            yield req
        else:
            for req in self.parse(response):
                req.dont_filter = True
                yield req

    def parse(self, response):
        base_url = get_base_url(response)

        categories = response.xpath('//ul[@class="main-nav"]/li/a/@href').extract()[1:]
        for url in categories:
            yield Request(urljoin_rfc(base_url, url),
                          cookies=self.additional_cookies)

        sub_categories = response.xpath('//div[@class="sidenav-title" and span/text()="Browse Categories"]'
                                        '/following-sibling::div[@class="inner"]//a/@href').extract()
        for url in sub_categories:
            yield Request(urljoin_rfc(base_url, url),
                          cookies=self.additional_cookies)

        per_page = set(response.xpath('//div[contains(@class, "showing-per-page")]//option/@value').extract())
        if per_page:
            per_page_param = url_query_parameter(response.url, 'productsPerPage')
            if per_page_param != '48':
                url = add_or_replace_parameter(response.url, 'productsPerPage', '48')
                url = add_or_replace_parameter(url, 'page', '0')
                yield Request(url, cookies=self.additional_cookies)
                return

            # Check for valid location
            is_valid, country_detected = self._is_valid_location(response)
            if not is_valid:
                reason = 'Wrong country detected: %s' % country_detected
                new_request = self._retry_request(response, self.parse, reason)
                if new_request:
                    yield new_request
                return

            # Parse products
            mde = MicrodataExtractor()
            data = mde.extract(response.body)
            if data:
                product_ids = response.xpath('//div[@itemtype="http://schema.org/Product"]/@data-id').extract()
                product_urls = map(lambda u: urljoin_rfc(base_url, u),
                    response.xpath('//div[@itemtype="http://schema.org/Product"]'
                                   '/div[@class="product-info"]/div[@class="title"]/a/@href').extract())
                product_imgs = map(lambda u: urljoin_rfc(base_url, u),
                    response.xpath('//div[@itemtype="http://schema.org/Product"]//a[@class="product-image"]'
                                   '//img[@class="product-image-file"]/@src').extract())
                rrp_prices = {}
                for product_id in product_ids:
                    rrp_price = response.xpath('//div[@data-id="%s"]//div/@data-tc-original-price' % product_id).extract()
                    if rrp_price:
                        rrp_prices[product_id] = rrp_price[0]

                products_extra_data = {}
                for product_id, product_url, product_img in zip(product_ids, product_urls, product_imgs):
                    products_extra_data[product_id] = {
                        'url': product_url,
                        'image_url': product_img,
                    }

                category = ''
                categories = filter(lambda item: item['type'] == 'http://data-vocabulary.org/Breadcrumb', data['items'])
                if categories:
                    category = categories[0]['properties']['title'][1]
                brands = set(response.xpath('//div[@class="filter-brand-wrapper"]'
                                            '//label[contains(@for, "product-listings__filter-top-brands-")]/a[@disabled]/text()')\
                             .re(r'(.*) \('))
                products = filter(lambda item: item.get('type', '') == 'http://schema.org/Product', data['items'])
                for product in products:
                    product_id = product['properties']['productId']
                    ajax_url = self.AJAX_URL % product_id
                    headers = {'X-Requested-With': 'XMLHttpRequest'}
                    req = Request(ajax_url,
                                  headers=headers,
                                  callback=self.parse_options,
                                  meta={'main_product': product['properties'],
                                        'category': category,
                                        'products_extra': products_extra_data,
                                        'brands': brands,
                                        'rrp_prices': rrp_prices,
                                        'proxy': response.meta.get('proxy'),
                                        'proxy_service_disabled': True},
                                  cookies=self.additional_cookies)
                    yield req

                # Check for next page and follow this if exists
                next_page = response.xpath('//li[@class="next"]/a/@href').extract()
                if next_page:
                    yield Request(urljoin_rfc(get_base_url(response), next_page[0]),
                                  cookies=self.additional_cookies)

    def parse_simple(self, response):
        # Check for valid location
        is_valid, country_detected = self._is_valid_location(response)
        if not is_valid:
            reason = 'Wrong country detected: %s' % country_detected
            new_request = self._retry_request(response, self.parse_simple, reason)
            if new_request:
                yield new_request
            return

        self._load_matched_main_products()
        for product_sku, main_product in self.main_products.items():
            ajax_url = self.AJAX_URL % product_sku
            headers = {'X-Requested-With': 'XMLHttpRequest'}
            req = Request(ajax_url,
                          headers=headers,
                          callback=self.parse_options,
                          meta={'main_product': main_product,
                                'handle_httpstatus_all': True,
                                'dont_retry': True,
                                'proxy': response.meta.get('proxy'),
                                'proxy_service_disabled': True},
                          cookies=self.additional_cookies)
            yield req

    def parse_options(self, response):
        if response.status == 500:
            return
        elif response.status in (403, 503):
            # reason = 'Spider blocked in %s' %  response.url
            # new_request = self._retry_request(response, self.parse_options, reason, False)
            # if new_request:
            #    yield new_request
            return

        data = json.loads(response.body)

        # Extract main product data
        if self._full_run:
            main_product_data = response.meta['main_product']
            category = response.meta['category']
            products_extra = response.meta['products_extra']
            brands_filter_data =  response.meta['brands']
            rrp_prices = response.meta['rrp_prices']

            product_id = main_product_data['productId']
            product_name = main_product_data['name']
            product_url = products_extra[product_id]['url']
            product_brand = ''
            for brand in brands_filter_data:
                if product_name.startswith(brand):
                    product_brand = brand
                    break

            product_identifier = product_id.upper()
            product_sku = product_id
            product_image = products_extra[product_id]['image_url']
            product_rrp = rrp_prices.get(product_id, '')
        else:
            main_product = response.meta['main_product']
            category = main_product['category']
            product_name = main_product['name']
            product_url = main_product['url']
            product_brand = main_product['brand']
            product_identifier = main_product['sku']
            product_sku = main_product['sku']
            product_image = main_product['image_url']
            product_rrp = main_product['rrp']

        # Create main product loader and populate fields with above data
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', product_identifier)
        loader.add_value('sku', product_sku)
        loader.add_value('name', product_name.split(' - ')[0].strip())
        loader.add_value('url', product_url)
        loader.add_value('brand', product_brand)
        if category:
            loader.add_value('category', category)
        if product_image:
            loader.add_value('image_url', product_image)

        product_item = loader.load_item()

        # Check product options
        for product in data['stockAvailabilityList']:
            option_item = Product(product_item)
            option_item['identifier'] = product_item['identifier'] + '-' + product['colourCode'] + product['sizeCode']
            option_item['sku'] = product_sku
            option_item['name'] = (product_item['name'] + ' - ' + product['name']).strip()
            if (not product['stock']) or ('discontinued' in product['stock'].lower()):
                continue
            elif not 'in stock' in product['stock'].lower():
                option_item['stock'] = 0
            option_item['price'] = extract_price(product['price'])

            option_item_copy = dict(option_item)
            option_item_copy['rrp'] = product_rrp
            self._products.append(option_item_copy)

            if self.extract_rrp:
                metadata = EvansMeta()
                metadata['rrp'] = product_rrp
                option_item['metadata'] = metadata

            yield option_item

    def _is_valid_location(self, response):
        try:
            country_selected = response.xpath('//span[@id="mini_basket_change_delivery_country"]/img/@alt').extract()[0]
        except:
            try:
                country_selected = response.xpath('//select[@id="country-dd"]/option[@selected]/@value').extract()[0]
            except:
                country_selected = 'N/A'
        return (country_selected == self.country), country_selected

    def _retry_request(self, response, callback, reason, set_location=True):
        new_request = None
        retry_no = int(response.meta.get('retry_no', 0))
        if retry_no < self.max_retry:
            self.log('RETRYING => %s' % reason)
            retry_no += 1
            if set_location:
                form_xpath = '//form[@id="country-and-currency-form"]'
                headers = {'Referer': response.url}
                meta = {'dont_cache': True,
                        'retry_no': retry_no}
                if 'proxy' in response.meta:
                    meta['proxy'] = response.meta['proxy']
                    meta['proxy_service_disabled'] = True
                req = FormRequest.from_response(response,
                                                formdata=self.location_settings,
                                                formxpath=form_xpath,
                                                headers=headers,
                                                meta=meta,
                                                dont_filter=True,
                                                callback=callback)
                new_request = req
            else:
                new_request = response.request.copy()
                new_request.meta['retry_no'] = retry_no
        else:
            self.log('GAVE UP RETRYING => %s' % reason)

        return new_request

    def _load_extra_data(self):
        products_extra = {}
        if hasattr(self, 'prev_crawl_id'):
            meta_filename = os.path.join(DATA_DIR, 'meta/%s_meta.json-lines' % self.prev_crawl_id)
            if os.path.exists(meta_filename):
                with open(meta_filename) as f:
                    for l in f:
                        json_d = l.strip()
                        if json_d:
                            data = json.loads(json_d)
                            sku = data.get('sku', '').upper()
                            if sku and sku not in products_extra:
                                products_extra[sku] = \
                                    {'sku': sku,
                                     'rrp': data.get('metadata', {}).get('rrp', ''),
                                     'brand': data.get('brand', ''),
                                     'image_url': data.get('image_url', '')}
        else:
            self.log('EvansCycles Base Spider ERROR => Previous crawl ID does not found')
        return products_extra

    def _load_matched_main_products(self):
        api_host = API_ROOTS['new_system']
        api_key = API_KEY
        compmon_api = Compmon2API(api_host, api_key)
        products_extra = self._load_extra_data()
        if not products_extra:
            self.log('EvansCycles Base Spider ERROR => Not products extra')
        ignore_skus = []
        for website_id in self.simple_run_websites:
            matched_products = compmon_api.get_matched_products(website_id)
            for p in matched_products:
                # IE: EV247221-NA-BLK => EV247221
                p_sku = p['identifier'].split('-')[0]
                if (p_sku not in self.main_products) and (p_sku not in ignore_skus):
                    extra_data = {}
                    if p_sku in products_extra:
                        extra_data = products_extra[p_sku]
                    self.main_products[p_sku] = {
                        'category': p['category'],
                        'name': p['name'],
                        'url': p['url'],
                        'brand': extra_data.get('brand', ''),
                        'sku': p_sku,
                        'image_url': extra_data.get('image_url', ''),
                        'rrp': extra_data.get('rrp', ''),
                    }

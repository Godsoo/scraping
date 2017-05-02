# -*- coding: utf-8 -*-
import urllib
import time
import json
import re
import csv
from copy import deepcopy
from decimal import Decimal
from urlparse import urljoin as urljoin_rfc
from urlparse import urlparse
from urlparse import parse_qs

try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider
from scrapy.exceptions import CloseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import url_query_parameter
from scrapy.utils.response import get_base_url
from scrapy.item import Item, Field
from scrapy.contrib.loader import XPathItemLoader
from scrapy.contrib.loader.processor import MapCompose, Join, TakeFirst
from scrapy.utils.markup import remove_entities
from scrapy import log

from product_spiders.utils import extract_price, fix_json
from product_spiders.items import Product, ProductLoaderWithNameStrip
from product_spiders.base_spiders.matcher import Matcher

from product_spiders.spiders.BeautifulSoup import BeautifulSoup
import hashlib


def filter_name(name):
    m = re.search(r"^new offers for", name, re.I)
    if m:
        found = m.group(0)
        res = name.replace(found, "")
        res = res.strip()
    else:
        res = name
    if len(res) > 1024:
        res = res.strip()[:1021] + '...'
    return res

def filter_brand(brand):
    """
    >>> a = "a" * 105
    >>> len(a) > 100
    True
    >>> len(filter_brand(a)) > 100
    False
    >>> a = u"a" * 99
    >>> len(a) > 100
    False
    >>> a += u"\u044b"
    >>> len(a) > 100
    False
    >>> len(a.encode('utf-8')) > 100
    True
    >>> len(filter_brand(a)) > 100
    False
    >>> len(filter_brand(a).encode('utf-8')) > 100
    True
    """
    if len(brand) > 100:
        brand = brand.strip()[:97] + '...'
    return brand


class AmazonProductLoader(ProductLoaderWithNameStrip):
    """
    >>> selector = HtmlXPathSelector(text="<html></html>")
    >>> loader = AmazonProductLoader(Product(), selector=selector)
    >>> loader.add_value('name', 'new offers for Lego asd')
    >>> loader.get_output_value('name')
    u'Lego asd'
    >>> loader.add_value('brand', 'a' * 200)
    >>> len(loader.get_output_value('brand')) <= 100  # 100 symbols maximum
    True
    >>> loader.replace_value('brand', u'Camille - Birtel, Wolfgang / Egelhof, Maria(E) Saint-Sa\xebns (Author), Wolfgang Birtel (Editor), Maria Egelhof (Editor)')
    >>> len(loader.get_output_value('brand')) <= 100
    True
    """
    name_in = MapCompose(ProductLoaderWithNameStrip.name_in, unicode.strip, filter_name)
    brand_in = MapCompose(ProductLoaderWithNameStrip.brand_in, filter_brand)


class Review(Item):
    date = Field()
    rating = Field()
    full_text = Field()
    url = Field()
    product_url = Field()
    sku = Field()

def extract_rating(s):
    r = re.search('(\d+)', s)
    if r:
        return int(r.groups()[0])

class ReviewLoader(XPathItemLoader):
    date_in = MapCompose(unicode, unicode.strip)
    date_out = TakeFirst()

    rating_in = MapCompose(unicode, extract_rating)
    rating_out = TakeFirst()

    full_text_in = MapCompose(unicode, unicode.strip, remove_entities)
    full_text_out = Join()

    url_in = MapCompose(unicode, unicode.strip)
    url_out = TakeFirst()

    product_url_in = MapCompose(unicode, unicode.strip)
    product_url_out = TakeFirst()

    sku_in = MapCompose(unicode, unicode.strip, unicode.lower)
    sku_out = TakeFirst()


class AmazonMeta(Item):
    reviews = Field()
    brand = Field()
    universal_identifier = Field()


class BaseAmazonSpider(BaseSpider):
    """ Exclude following sellers from results """
    exclude_sellers = []
    """ Monitor  only the following sellers"""
    sellers = []
    """ Collect all products found. If false, collects only lowest priced product """
    all_sellers = False
    """ Max search result pages to crawl """
    max_pages = None
    """ Custom errors """
    errors = []

    """ Use unique amazon identifier """
    _use_amazon_identifier = None

    """ Collect products from results list """
    collect_products_from_list = False

    """ Collect products only from results list and grab the dealer of this product (buybox) """
    only_buybox = False

    """ retry counter limit """
    max_retry_count = 15

    """ pause in seconds between retries """
    retry_sleep = 60

    """ Should the spider retry or not """
    do_retry = False

    """ Collect New products """
    collect_new_products = True

    """ Collect Used products """
    collect_used_products = True

    """ Only products sold by Amazon. """
    amazon_direct = False

    """ Parse options from product page. WARNING: experimental feature.
    Please test before uploading to production. Any fixes are welcomed """
    parse_options = False

    """ Collect products all product even without dealer. WARNING: experimental feature.
    Please test before uploading to production. Any fixes are welcomed """
    collect_products_with_no_dealer = False

    """ Collect reviews for products """
    collect_reviews = False
    """ Collect reviews once per product
    (meaning that if dealers are being collected, only one of products will have reviews) """
    reviews_once_per_product_without_dealer = True

    review_date_format = u'%d/%m/%Y'

    seller_id_required = False

    """ Filename for file with brand and sellers cache """
    cache_filename = None

    deduplicate_identifiers = True

    def __init__(self, *args, **kwargs):
        self.errors = []

        if not hasattr(self, 'domain'):
            if 'domain' in kwargs:
                self.domain = kwargs['domain']
            elif len(args) > 0:
                self.domain = args[0]
                args = args[1:]
            else:
                msg = "Should have attr `domain` set. Using default 'amazon.com'"
                self.log(msg, level=log.ERROR)
                self.errors.append(msg)
                self.domain = 'amazon.com'

        super(BaseAmazonSpider, self).__init__(*args, **kwargs)

        self.allowed_domains = [self.domain]
        self.matcher = Matcher(self.log)
        self.try_suggested = True
        self.items_not_found_callback = None

        if self._use_amazon_identifier is None:
            if self.all_sellers:
                self._use_amazon_identifier = True
            else:
                self._use_amazon_identifier = False

        if self.only_buybox or self.amazon_direct:
            self.collect_products_from_list = True

        if self.amazon_direct:
            self.all_sellers = False

        if self.all_sellers:
            self._collect = self._collect_all
        else:
            self._collect = self._collect_lowest_price

        self.reviews_collected_for = {}

        self.sellers_cache = {}
        self.brands_cache = {}

        if self.cache_filename:
            with open(self.cache_filename) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not self._use_amazon_identifier:
                        self.brands_cache[row['identifier'].strip()] = row['brand']
                        self.sellers_cache[row['identifier']] = row['dealer']
                    else:
                        self.brands_cache[row['identifier'].split(':')[1].strip()] = row['brand']
                        try:
                            self.sellers_cache[row['identifier'].split(':')[2].strip()] = row['dealer']
                        except IndexError:
                            continue

    def _append_request(self, url, callback, meta):
        if self.do_retry:
            meta['requests'].append(Request(url,
                                            callback=callback,
                                            meta=meta,
                                            dont_filter=True,
                                            errback=lambda failure,
                                                           url=url,
                                                           metadata=meta: self.retry_download(failure,
                                                                                              url,
                                                                                              metadata,
                                                                                              callback)))
        else:
            meta['requests'].append(Request(url, callback=callback, meta=meta, dont_filter=True))

    def _append_request_suggested(self, url, callback, meta):
        meta = dict(meta)
        meta['suggested_search_peek'] = True
        if self.do_retry:
            meta['requests'].append(Request(url,
                                            callback=callback,
                                            meta=meta,
                                            dont_filter=True,
                                            errback=lambda failure,
                                                           url=url,
                                                           metadata=meta: self.retry_download(failure,
                                                                                              url,
                                                                                              metadata,
                                                                                              callback)))
        else:
            meta['requests'].append(Request(url, callback=callback, meta=meta, dont_filter=True))

    def get_url_from_asin(self, asin):
        url = 'http://%s/gp/product/%s/?ref=twister_dp_update&ie=UTF8&psc=1' % (self.domain, asin)
        return url

    def start_requests(self):
        raise NotImplementedError('Implement start_requests!')

    def match(self, search_item, new_item):
        raise NotImplementedError('Implement match!')

    # Basic coincidence is tested before entering the list of suppliers for example
    def basic_match(self, search_item, new_item):
        return True

    def _filter_reviews(self, new_item):
        identifier = new_item['identifier']
        amazon_identifier = None
        for x in identifier.split(":"):
            if len(x) > 0:
                amazon_identifier = x
                break
        collect_reviews = True
        # if reviews already being collected for other product with same sku
        if self.reviews_once_per_product_without_dealer:
            if amazon_identifier in self.reviews_collected_for \
                    and self.reviews_collected_for[amazon_identifier] != identifier:
                collect_reviews = False
            if amazon_identifier not in self.reviews_collected_for:
                self.reviews_collected_for[amazon_identifier] = identifier

        if 'metadata' in new_item:
            if not collect_reviews:
                if 'reviews' in new_item['metadata']:
                    del (new_item['metadata']['reviews'])
            else:
                new_item['metadata']['universal_identifier'] = amazon_identifier
        return new_item

    def _filter_item(self, new_item):
        new_item = self._filter_reviews(new_item)
        return new_item

    def _collect_all(self, collected_items, new_item):
        """ Collects all products """
        new_item = self._filter_item(new_item)
        for i, item in enumerate(collected_items):
            if new_item['identifier'] == item['identifier']:
                if new_item['price'] != item['price']:
                    self.log('Product %s has different prices %s and %s' % (new_item['identifier'],
                                                                            new_item['price'], item['price']))
                    item['price'] = min(item['price'], new_item['price'])
                return False
        collected_items.append(new_item)
        return True

    def _may_collect(self, collected_items, new_item):
        if not self.all_sellers and collected_items:
            # Got lower price already
            i = collected_items[0]
            if Decimal(i['price']) < Decimal(new_item['price']):
                return False
        return True

    def _collect_lowest_price(self, collected_items, new_item):
        """ Keeps only product with the lowest price """
        new_item = self._filter_item(new_item)
        if collected_items:
            i = collected_items[0]
            if Decimal(i['price']) > Decimal(new_item['price']):
                collected_items[0] = new_item
        else:
            collected_items.append(new_item)

    def _collect_best_match(self, collected_items, new_item, search):
        """ Keeps only product with the lowest price """
        new_item = self._filter_item(new_item)
        if collected_items:
            i = collected_items[0]
            match_threshold = self.matcher.match_ratio(search, i['name'], None)
            if self.match_text(search, new_item, match_threshold):
                collected_items[0] = new_item
        else:
            collected_items.append(new_item)

    # Only if Proxy Service enabled
    def proxy_service_check_response(self, response):
        return self.antibot_protection_raised(response.body)

    def extract_price(self, price):
        return extract_price(price)

    def match_price(self, search_item, new_item, price_diff=0.5):
        """ Checks price variation """
        search_price = Decimal(search_item['price']) if search_item['price'] else 0
        diff = Decimal(search_price) * Decimal(price_diff)
        matches = search_price - diff <= Decimal(new_item['price']) <= search_price + diff
        if not matches:
            self.log('Item price is too different from %s, reject %s' % (search_price, new_item))
        return matches

    def match_name(self, search_item, new_item, match_threshold=90, important_words=None):
        r = self.matcher.match_ratio(search_item['name'], new_item['name'], important_words)
        return r >= match_threshold

    def match_text(self, text, new_item, match_threshold=90, important_words=None):
        r = self.matcher.match_ratio(text, new_item['name'], important_words)
        return r >= match_threshold

    def search(self, search_string, search_item):
        url = 'http://%s/s/ref=nb_sb_noss?url=search-alias%%3Daps&field-keywords=%s'
        if self.amazon_direct:
            if '.com' in self.domain:
                url += '&emi=ATVPDKIKX0DER'
            elif '.co.uk' in self.domain:
                url += '&emi=A3P5ROKL5A1OLE'
            elif '.fr' in self.domain:
                url += '&emi=A1X6FK5RDHNB96'
            elif '.it' in self.domain:
                url += '&emi=A11IL2PNWYJU7H'
            else:
                raise CloseSpider('Domain %s not found!!' % self.domain)
        self.log('Searching for [%s]' % search_string)
        return Request(url % (self.domain, urllib.quote_plus(search_string)),
                       meta={'search_string': search_string,
                             'search_item': search_item,
                             'collected_items': [],
                             'requests': [],
                             'current_page': 1,
                             'requests_done': set(),
                       }, dont_filter=True, callback=self.parse_product_list)

    def _continue_requests(self, response):
        while response.meta.get('requests', []):
            req = response.meta['requests'].pop(0)
            if req.url not in response.meta['requests_done']:
                response.meta['requests_done'].add(req.url)
                if '_product' in req.meta:
                    if not self._may_collect(response.meta['collected_items'], req.meta['_product']):
                        self.log('Skip product unlikely to be collected %s' % (req.meta['_product']))
                        continue
                yield req
                return

        if not response.meta.get('collected_items') and self.items_not_found_callback:
            self.items_not_found_callback(response.meta['search_string'], response.meta['search_item'])

        for item in response.meta.get('collected_items', []):
            loader = AmazonProductLoader(Product(), response=response)
            for field, value in item.items():
                if field != 'metadata':
                    try:
                        loader.add_value(field, value)
                    except UnicodeDecodeError:
                        loader.add_value(field, value.decode('utf-8', errors='ignore'))
            res = loader.load_item()
            if 'metadata' in item:
                res['metadata'] = item['metadata']
            yield res

    def _seller_ok(self, seller):
        for exclude in self.exclude_sellers:
            if seller.lower() == exclude.lower():
                self.log('>>> Excluding seller name => %s' % seller)
                return False

        if self.sellers:
            for monitor_seller in self.sellers:
                if seller.lower() == monitor_seller.lower():
                    return True
            self.log('>>> Excluding seller name => %s' % seller)
            return False
        return True

    def parse_product(self, response):
        """ "Parse" product just to get seller name """
        if self.antibot_protection_raised(response.body):
            if self.do_retry:
                yield self.retry_download(failure=None,
                                          url=response.url,
                                          metadata=response.meta,
                                          callback=self.parse_product)
            else:
                self.log('WARNING: Amazon antibot protection detected, consider using proxy/tor, url: [{}]'.format(
                    response.url))

        hxs = HtmlXPathSelector(response)

        if self.parse_options:
            self.log("Options enabled")
            options = re.findall(r'var asin_variation_values = ({.*});  var stateData', response.body_as_unicode().replace('\n', ''))
            if not options:
                options = re.findall(r'asin_variation_values\":({.*}),\"vari', response.body.replace('\n', ''))

            display_data = re.findall(r'var dimensionValuesDisplayData = ({[^}]*})', response.body_as_unicode().replace('\n', ''))

            options = json.loads(options[0]) if options else {}
            display_data = json.loads(fix_json(display_data[0])) if display_data else {}

            if options and response.meta.get('parse_options', True):
                self.log('>>>> OPTIONS FOUND => %s' % response.url)

                for option_id in options.keys():
                    option_url = u'http://%s/gp/product/%s/?ref=twister_dp_update&ie=UTF8&psc=1' % (self.domain, option_id)
                    self.log('>>>> PROCESS OPTION ID %s => %s' % (option_id, option_url))
                    meta = response.meta.copy()
                    options_strs = None
                    option_text_extracted = False
                    if display_data:
                        if option_id in display_data:
                            options_strs = display_data[option_id]
                    try:
                        product_name = \
                            hxs.select(u'//div[@class="buying"]//span[@id="btAsinTitle"]/span/text()')\
                               .extract()[0].strip()
                        product_name = product_name[0:1020] + '...' if len(product_name) > 1024 else product_name
                        product_name = filter_name(product_name)
                        if options_strs:
                            product_name = product_name + ' (' + ', '.join(options_strs) + ')'
                            option_text_extracted = True
                    except IndexError:
                        self.log("Failed to parse option name on url: %s" % response.url)
                        continue
                    # set identifier, remove old option id
                    identifier_groups = response.meta['_product']['identifier'].split(':')
                    meta['_product']['identifier'] = ':'.join(identifier_groups[:2])

                    meta['_product']['name'] = product_name
                    base_product = dict(response.meta['_product'])
                    base_product = base_product[0] if type(base_product) == tuple else base_product
                    meta['base_product'] = base_product

                    meta['parse_options'] = False
                    meta['check_identifier'] = False
                    identifier_groups[1] = option_id
                    meta['option_identifier'] = ":".join(identifier_groups[:2])
                    meta['option_name'] = product_name
                    if not option_text_extracted:
                        meta['option_text_extracted'] = False
                    # response.meta['requests'].append(Request(option_url, dont_filter=True, callback=self.parse_product, meta=meta))
                    self._append_request(option_url, self.parse_product, meta)
                for x in self._continue_requests(response):
                    yield x
                return
            else:
                meta = response.meta.copy()
                base_product = meta.get('base_product', None)

                product = meta['_product']
                product = product[0] if type(product) == tuple else product
                product = deepcopy(product)

                if not response.meta.get('parse_options', True):
                    self.log('>>> PARSE OPTION')
                    identifier_groups = product['identifier'].split(':')
                    identifier = hxs.select("//input[@id='ASIN']/@value").extract()
                    if identifier:
                        identifier = ':' + identifier[0] + ":".join(identifier_groups[2:])
                    else:
                        identifier = base_product['identifier']
                    self.log("Found identifier: %s" % identifier)
                    self.log("Meta identifier: %s" % meta['option_identifier'])
                    self.log("Meta product name: %s" % meta['option_name'])
                    product['identifier'] = meta['option_identifier']
                    product['name'] = meta['option_name']
                    option_text = hxs.select('//select[contains(@id, "dropdown_selected")]/option[@selected]/text()')\
                                     .extract()
                    if not meta.get('option_text_extracted', True) and option_text:
                        self.log('OPTION: ' + ''.join(option_text))
                        product['name'] = base_product['name'] + ' - ' + option_text[0].strip()
                price = self.collect_price(hxs, response)
                if not price:
                    no_price_ = True
                else:
                    product['price'] = price
                    no_price_ = False
                    # ignores product if it not comes from the dealers list
                if no_price_ and not response.meta.get('search_dealer', False):
                    self.log('ERROR: no price found! URL:{}'.format(response.url))
                    product['price'] = 0

                product['url'] = response.url
        else:
            product = deepcopy(response.meta['_product'])
            # product = response.meta['_product']

        if 'brand' not in product or not product['brand']:
            brand = hxs.select("//span[@class='brandLink']/a/text()").extract()
            if brand:
                product['brand'] = brand[0]

        vendor = hxs.select(u'//div[@class="buying"]//a[contains(@href,"seller/at-a-glance")]/text()').extract()
        if not vendor:
            vendor = hxs.select('//div[@id="soldByThirdParty"]/b/text()').extract()
        else:
            # check if it is taken from used products buy box, ignore it if so
            used_vendor = hxs.select(
                u'//div[@class="buying"]//a[contains(@href,"seller/at-a-glance")]/text()/../../../@id').extract()
            if used_vendor:
                vendor = None
        if not vendor:
            amazon_price = hxs.select('//span[@id="actualPriceValue"]/b/text()').extract()
            if not amazon_price:
                amazon_price = hxs.select('//span[@id="priceblock_ourprice"]/text()').extract()
                # Checks if it is an amazon product
            if amazon_price:
                vendor = 'Amazon'
        check_price = response.meta.get('check_price', False)
        if check_price:
            price = self.collect_price(hxs, response)
            if price:
                product['price'] = price

        if not vendor or check_price:
            self.log("No vendor or check price")
            offer_listing = hxs.select('//div[@id="olpDivId"]/span[@class="olpCondLink"]/a/@href').extract()
            if check_price and (not offer_listing or self.collect_products_from_list):
                price = self.collect_price(hxs, response)
                if not price:
                    no_price_ = True
                else:
                    product['price'] = price
                    no_price_ = False

                if no_price_:
                    self.log('ERROR: no price found! URL:{}'.format(response.url))
            elif not offer_listing or self.collect_products_from_list:
                if not self.only_buybox:
                    self.log('WARNING: No seller name => %s' % response.url)
                vendor = None
            else:
                self.log("PARSE OFFER LISTING")
                offer_listing_url = urljoin_rfc(get_base_url(response), offer_listing[0])
                params = parse_qs(urlparse(offer_listing_url).query)
                condition = params.get('condition', ['any'])[0].strip()
                if self.collect_new_products and condition == 'new' or \
                        self.collect_used_products and condition == 'used':
                    meta = response.meta
                    if 'check_price' in meta:
                        del(meta['check_price'])
                    self._append_request(offer_listing_url, self.parse_mbc_list, meta)
        else:
            self.log('Vendor')
            if vendor != "Amazon":
                vendor = 'AM - ' + vendor[0]

        if vendor:
            product['dealer'] = vendor
            if 'seller_id' in response.meta:
                self.sellers_cache[response.meta['seller_id']] = vendor

        if not 'image_url' in product or not product['image_url']:
            image_url = hxs.select("//img[@id='main-image']/@src").extract()
            if image_url:
                product['image_url'] = image_url[0]

        if 'image_url' in product and len(product['image_url']) > 1024:
            image_url = hxs.select('//img[@id="main-image-nonjs"]/@src').extract()
            if not image_url:
                image_data_json = hxs.select("//img[@id='landingImage']/@data-a-dynamic-image").extract()
                if image_data_json:
                    image_data = json.loads(image_data_json[0])
                    try:
                        product['image_url'] = image_data.keys()[0]
                    except:
                        self.errors.append('WARNING: No image url in %s' % response.url)
            else:
                product['image_url'] = image_url[0]

        if not 'brand' in product or not product['brand']:
            brand = hxs.select('//div[@class="buying"]/span[contains(text(), "by")]/a/text()').extract()
            if brand:
                product['brand'] = brand[0]

        if vendor or self.collect_products_with_no_dealer:
            if self._seller_ok(vendor):
                if 'search_item' not in response.meta or self.match(response.meta['search_item'], product):
                    if not product.get('shipping_cost', None):
                        shipping = hxs.select(
                            '//div[@id="buyboxDivId"]//span[@class="plusShippingText"]/text()').extract()
                        if not shipping:
                            shipping = hxs.select('//div[@id="soldByThirdParty"]/span[contains(@class, "shipping3P")]/text()').re(r'[\d.,]+')
                        if shipping:
                            product['shipping_cost'] = self.extract_price(shipping[0])
                    if self.collect_reviews and 'reviews_url' in response.meta \
                            and ('metadata' not in product or 'reviews' not in product['metadata']):
                        self._append_request(response.meta['reviews_url'], self.parse_review, response.meta)
                    elif 'mbc_list_url' in response.meta:
                        self._append_request(response.meta['mbc_list_url'], self.parse_mbc_list, response.meta)
                    else:
                        if response.meta.get('matches_search', False):
                            source = "matches"
                        else:
                            source = "search"
                        self.log("Collecting items from %s. Identifier: %s, price: %s" %
                                 (source, product['identifier'], str(product['price'])))
                        if not 'collected_items' in response.meta:
                            response.meta['collected_items'] = []
                        self._collect(response.meta['collected_items'], product)

        for x in self._continue_requests(response):
            yield x

    def parse_product_list(self, response):

        if self.antibot_protection_raised(response.body):
            if self.do_retry:
                yield self.retry_download(failure=None,
                                          url=response.url,
                                          metadata=response.meta,
                                          callback=self.parse_product_list)
            else:
                self.log('WARNING: Amazon antibot protection detected, consider using proxy/tor, url: [{}]'.format(
                    response.url))

        hxs = HtmlXPathSelector(response)

        matched_any = False
        suggested_product_list = response.meta.get('suggested_search_peek', False)

        results = hxs.select(u'//div[@id="atfResults" or @id="btfResults"]//div[starts-with(@id, "result_")]')
        if not results:
            results = hxs.select('//li[@data-asin and contains(@id, "result_")]')

        '''
        with open('%s.html' % hashlib.md5(response.url).hexdigest(), 'w') as f:
            f.write(response.body)
        '''

        # Follow suggested links only on original search page
        if not suggested_product_list and not results and self.try_suggested:
            urls = hxs.select(u'//div[contains(@class,"fkmrResults")]//h3[@class="fkmrHead"]//a/@href').extract()
            results = hxs.select(u'//div[contains(@class,"fkmrResults")]//div[starts-with(@id, "result_")]')
            if urls:
                self.log('No results found for [%s], trying suggested searches' % (response.meta['search_string']))
                for url in urls:
                    url = urljoin_rfc(get_base_url(response), url)
                    self._append_request_suggested(url, self.parse_product_list, response.meta)
            if results:
                self.log('No results found for [%s], using suggested products' % (response.meta['search_string']))
            if not urls and not results:
                self.log('No results found for [%s], no suggestions' % (response.meta['search_string']))

        preloaded_images = hxs.select('//div[@id="results-atf-images-preload"]/img/@src').extract()
        preloaded_images.reverse()

        for result in results:
            try:
                product_name = result.select(u'.//h3/a/span/text()').extract()
                if product_name and product_name[0].endswith('...'):
                    new_product_name = result.select(u'.//h3/a/span/@title').extract()
                    if new_product_name:
                        product_name = new_product_name

                if not product_name:
                    product_name = result.select(u'.//h3/a/text()').extract()
                    if product_name and product_name[0].endswith('...'):
                        new_product_name = result.select(u'.//h3/a/@title').extract()
                        if new_product_name:
                            product_name = new_product_name

                if not product_name:
                    product_name = result.select(u'.//h2/text()').extract()

                product_name = product_name[0].strip()
                product_name = product_name[0:1020] + '...' if len(product_name) > 1024 else product_name
            except:
                continue

            try:
                identifier = result.select('./@name').extract()
                if not identifier:
                    identifier = result.select('@data-asin').extract()
                if not identifier:
                    raise AmazonScraperException("Could not extract identifier for product \"%s\" from page: %s" %
                                                 (product_name, response.url))
                identifier = identifier[0].strip()
            except:
                if not result.select('./@id').extract()[0].endswith('_empty'):
                    raise
                continue

            price = result.select('.//span[@class="bld lrg red"]//text()').extract()
            if not price:
                price = result.select('.//span[contains(@class, "a-color-price")]//text()').extract()
            if not price:
                price = result.select('.//span[contains(@class, "price")]//text()').extract()
            if not price:
                self.log('No price on %s' % response.url)
                continue

            price = self.extract_price(price[0])
            product = Product(response.meta['search_item'])
            product['name'] = filter_name(product_name)
            brand = result.select(u'.//h3/span[contains(text(),"by")]/text()').extract()
            if brand:
                product['brand'] = brand[0].replace('by ', '').replace('de ', '').replace('(', '').strip()
            product['price'] = price

            if self._use_amazon_identifier:
                product['identifier'] = product.get('identifier', '') + ':' + identifier

            if self.cache_filename:
                if self._use_amazon_identifier:
                    brand = self.brands_cache.get(identifier, '')
                else:
                    brand = self.brands_cache.get(product['identifier'], '')

                product['brand'] = brand

            if preloaded_images:
                pre_image_url = preloaded_images.pop()
            else:
                pre_image_url = ''

            try:
                url = result.select(u'.//h3/a/@href').extract()[0]
            except:
                url = result.select(u'.//a/@href').extract()[0]
            product['url'] = urljoin_rfc(get_base_url(response), url)
            image_url = result.select(u'.//img[contains(@class, "productImage")]/@src').extract()
            if not image_url:
                image_url = result.select(u'.//a/img/@src').extract()
            if image_url:
                product['image_url'] = urljoin_rfc(get_base_url(response), image_url[0])
                if len(product['image_url']) > 1024 and ('data:image/jpg;base64' in product['image_url']) and pre_image_url:
                    product['image_url'] = pre_image_url

            meta = dict(response.meta)
            meta['_product'] = product
            reviews_url = result.select(u'ul/li/span[@class="rvwCnt"]/a/@href').extract()
            if not reviews_url:
                reviews_url = result.select(u'.//a[contains(@href, "product-reviews")]/@href').extract()
            if reviews_url:
                reviews_url = reviews_url[0]
                meta['reviews_url'] = urljoin_rfc('http://www.amazon.com', reviews_url)

            if self.basic_match(response.meta['search_item'], product):
                more_buying_choices = \
                    result.select('.//li[@class="sect mbc"]/../li[contains(@class,"mkp2")]/a/@href').extract()
                if not more_buying_choices:
                    more_buying_choices = result.select('.//li[contains(@class,"mkp2")]/a/@href').extract()
                if not more_buying_choices:
                    more_buying_choices = result.select('.//a[contains(@href,"offer-listing") and contains(@href, "condition=")]/@href').extract()
                if more_buying_choices:
                    mbc_url = urljoin_rfc(get_base_url(response), more_buying_choices[0])
                    params = parse_qs(urlparse(mbc_url).query)
                    condition = params.get('condition', ['any'])[0].strip()
                    if not self.collect_new_products and condition == 'new':
                        continue
                    if not self.collect_used_products and condition == 'used':
                        continue
                    if not self.collect_products_from_list and more_buying_choices:
                        meta['mbc_list_url'] = mbc_url

                if self.match(response.meta['search_item'], product):
                    matched_any = True
                    if self.collect_reviews and reviews_url:
                        # collect reviews, then parse mbc list
                        self._append_request(reviews_url, self.parse_review, meta)
                    else:
                        if not self.collect_products_from_list and more_buying_choices:
                            self._append_request(meta['mbc_list_url'], self.parse_mbc_list, meta)
                        elif self.collect_products_from_list and not self.only_buybox:
                            if self.amazon_direct:
                                # Dealer to Amazon and collect best match
                                product['dealer'] = 'Amazon'
                                search_item_name = response.meta['search_item'].get('name', '')
                                search_string = ' '.join([response.meta['search_string'], search_item_name]).strip()
                                yield self._collect_best_match(response.meta['collected_items'],
                                                               product,
                                                               search_string)
                            else:
                                yield self._collect_all(response.meta['collected_items'],
                                                        product)
                        else:
                            # Go and extract vendor
                            self._append_request(product['url'], self.parse_product, meta)
                else:
                    if not self.cache_filename:
                        self._append_request(product['url'], self.parse_product, meta)

        next_url = hxs.select(u'//a[@id="pagnNextLink"]/@href').extract()
        # Follow to next pages only for original search
        # and suggested search if at least one product matched from first page
        # otherwise it tries to crawl the whole Amazon or something like that
        if next_url and (not suggested_product_list or matched_any):
            page = response.meta.get('current_page', 1)
            if self.max_pages is None or page <= self.max_pages:
                response.meta['suggested_search_peek'] = False
                response.meta['current_page'] = page + 1
                url = urljoin_rfc(get_base_url(response), next_url[0])
                self._append_request(url, self.parse_product_list, response.meta)
            else:
                self.log('Max page limit %d reached' % self.max_pages)

        for x in self._continue_requests(response):
            yield x

    def parse_mbc_list(self, response):
        """ Parses list of more buying choices
            All products have the same id, so create a unique id from product id + seller id
        """

        if self.antibot_protection_raised(response.body):
            if self.do_retry:
                yield self.retry_download(failure=None,
                                          url=response.url,
                                          metadata=response.meta,
                                          callback=self.parse_mbc_list)
            else:
                self.log('WARNING: Amazon antibot protection detected, consider using proxy/tor, url: [{}]'.format(
                    response.url))

        hxs = HtmlXPathSelector(response)

        try:
            url = hxs.select('//a[@id="olpDetailPageLink"]/@href').extract()[0]
            url = urljoin_rfc(get_base_url(response), url)
            url_parts = url.split('/')
            product_id = url_parts[url_parts.index('product') + 1]
        except:
            if self.do_retry:
                yield self.retry_download(failure=None,
                                          url=response.url,
                                          metadata=response.meta,
                                          callback=self.parse_mbc_list)

        for result in hxs.select('//div[@id="olpOfferList"]//div[contains(@class, "olpOffer")]'):
            seller_id = None
            seller_urls = result.select(u'.//*[contains(@class, "olpSellerName")]//a/@href').extract()
            if seller_urls:
                seller_url_ = seller_urls[0]
                if 'seller=' in seller_url_:
                    seller_id = url_query_parameter(seller_url_, 'seller')
                else:
                    seller_parts = seller_url_.split('/')
                    try:
                        seller_id = seller_parts[seller_parts.index('shops') + 1]
                    except:
                        # External website (link "Shop this website"?)
                        seller_id = url_query_parameter(seller_url_, 'merchantID')
                        # else:
                #    seller_urls = result.select(u'.//ul[@class="sellerInformation"]//a/@href').extract()
            #    for s in seller_urls:
            #        if 'seller=' in s:
            #            seller_id = s.split('seller=')[1].split('&')[0]
            #            break

            try:
                price = self.extract_price(result.select('.//span[contains(@class, "olpOfferPrice")]/text()').extract()[0].strip())
            except:
                # TODO: Add to cart to see product details?
                continue
            product = Product(response.meta['search_item'])
            if '_product' in response.meta and 'metadata' in response.meta['_product']:
                product['metadata'] = deepcopy(response.meta['_product']['metadata'])
            product['name'] = filter_name(' '.join(hxs.select(u'//div[@id="olpProductDetails"]/h1//text()').extract()).strip())
            brand = hxs.select(u'//div[@id="olpProductByline"]/text()').extract()
            if brand:
                product['brand'] = brand[0].replace('by ', '').replace('de ', '').strip()
            product['price'] = price

            if seller_id:
                if self._use_amazon_identifier:
                    product['identifier'] = product.get('identifier', ':' + product_id) + ':' + seller_id
                product['url'] = 'http://%s/gp/product/%s/?m=%s' % (self.domain, product_id, seller_id)
                self.log('SELLER FOUND => %s - %s' % (product['identifier'], product['url']))
            else:
                if self._use_amazon_identifier:
                    product['identifier'] = product.get('identifier', '') + ':' + product_id
                product['url'] = 'http://%s/gp/product/%s/' % (self.domain, product_id)

            shipping = result.select('.//span[@class="olpShippingPrice"]/text()').extract()
            if shipping:
                product['shipping_cost'] = self.extract_price(shipping[0])

            image_url = hxs.select(u'//div[@id="olpProductImage"]//img/@src').extract()
            if image_url:
                product['image_url'] = urljoin_rfc(get_base_url(response), image_url[0])

            vendor = result.select(u'.//div[contains(@class, "olpSellerColumn")]//img/@title').extract()
            if not vendor:
                vendor = result.select(u'.//*[contains(@class, "olpSellerName")]//a/b/text()').extract()
            if not vendor:
                vendor = result.select(u'.//*[contains(@class, "olpSellerName")]//span/a/text()').extract()
            if vendor:
                vendor = vendor[0]
                if vendor.lower().startswith('amazon.'):
                    vendor = 'Amazon'
                else:
                    vendor = 'AM - ' + vendor
                self.sellers_cache[seller_id] = vendor
                product['dealer'] = vendor
                if self._seller_ok(vendor):
                    self.log('SELLER OK => %s' % vendor)
                    if self.match(response.meta['search_item'], product):
                        self.log('>>> COLLECTED ITEM => %s' % product['name'])
                        if response.meta.get('matches_search', False):
                            source = "matches"
                        else:
                            source = "search"
                        self.log("Collecting items from %s. Identifier: %s, price: %s" %
                                 (source, product['identifier'], str(product['price'])))
                        self._collect(response.meta['collected_items'], product)
                    else:
                        self.log('NO MATCH!!')
            elif seller_id in self.sellers_cache or product['identifier'] in self.sellers_cache:
                vendor = self.sellers_cache.get(seller_id) or self.sellers_cache.get(product['identifier'])
                product['dealer'] = vendor
                if self._seller_ok(vendor):
                    self.log('SELLER OK => %s' % vendor)
                    if self.match(response.meta['search_item'], product):
                        self.log('>>> COLLECTED ITEM => %s' % product['name'])
                        if response.meta.get('matches_search', False):
                            source = "matches"
                        else:
                            source = "search"
                        self.log("Collecting items from %s. Identifier: %s, price: %s" %
                                 (source, product['identifier'], str(product['price'])))
                        self._collect(response.meta['collected_items'], product)
                    else:
                        self.log('NO MATCH!!')
            elif (not self.seller_id_required) or seller_id:
                meta = dict(response.meta)
                meta['_product'] = product
                meta['seller_id'] = seller_id
                if 'mbc_list_url' in meta:
                    del (meta['mbc_list_url'])
                    # Go and extract vendor
                self._append_request(product['url'], self.parse_product, meta)

        next_url = hxs.select('//ul[@class="a-pagination"]/li[@class="a-last"]/a/@href').extract()
        # Collecting all items
        if self.all_sellers and next_url:
            url = urljoin_rfc(get_base_url(response), next_url[0])
            self._append_request(url, self.parse_mbc_list, response.meta)

        for x in self._continue_requests(response):
            yield x

    @staticmethod
    def antibot_protection_raised(text):
        """
        Checks if Amazon suspects our spider as a bot, consider using proxy/tor if so
        """
        if 'Sorry, we just need to make sure' in text:
            if 're not a robot' in text:
                return True
        return False

    def retry_download(self, failure, url, metadata, callback):
        no_try = metadata.get('try', 1)
        self.log("Try %d. Retrying to download %s" %
                 (no_try, url))
        if no_try < self.max_retry_count:
            metadata['try'] = no_try + 1
            metadata['recache'] = True
            time.sleep(self.retry_sleep)
            return Request(url,
                           callback=callback,
                           meta=metadata,
                           dont_filter=True,
                           errback=lambda failure,
                                          url=url,
                                          metadata=metadata: self.retry_download(failure, url, metadata, callback)
            )

    def parse_review(self, response):
        hxs = HtmlXPathSelector(response)
        soup = BeautifulSoup(response.body)
        if self.antibot_protection_raised(response.body):
            self.log(
                'WARNING: Amazon antibot protection detected, consider using proxy/tor, url: [{}]'.format(response.url))
            for x in self._continue_requests(response):
                yield x

        product = response.meta['_product']
        reviews = hxs.select(u'//table[@id="productReviews"]//div[@style="margin-left:0.5em;"]')

        for review in reviews:
            loader = ReviewLoader(item=Review(), selector=hxs, date_format=u'%m/%d/%Y')
            date = self._extract_review_date(review)
            res = None
            date_formats = (u'%B %d, %Y', u'%d %b %Y', u'%d %B %Y')
            for format in date_formats:
                try:
                    res = time.strptime(date, format)
                except ValueError:
                    pass
                if res:
                    break
            date = time.strftime(self.review_date_format, res)
            loader.add_value('date', date)

            rating = self._extract_review_rating(review)
            rating = int(float(rating))
            loader.add_value('rating', rating)
            loader.add_value('url', response.url)

            title = review.select(u'.//b/text()')[0].extract()
            text = ''.join([s.strip() for s in review.select(u'div[@class="reviewText"]/text()').extract()])
            loader.add_value('full_text', u'%s\n%s' % (title, text))

            loader.add_value('product_url', product['url'])
            loader.add_value('sku', product['sku'])

            if not 'metadata' in product:
                metadata = AmazonMeta()
                metadata['reviews'] = []
                product['metadata'] = metadata

            product['metadata']['reviews'].append(loader.load_item())

        response.meta['_product'] = product

        next_url = hxs.select("//a[contains(text(), 'Next')][contains(@href, 'product-reviews')]/@href").extract()
        if next_url:
            next_url = next_url[0]
            if next_url == '#':
                current_page = int(url_query_parameter(response.url, 'pageNumber', '1'))
                next_page = current_page + 1
                next_url = add_or_replace_parameter(response.url, 'pageNumber', str(next_page))

            self._append_request(next_url, self.parse_review, response.meta)
        else:
            self.log("PARSING REVIEWS COMPLETE FOR: %s" % product['identifier'])
            if 'metadata' in product:
                if 'reviews' in product['metadata']:
                    self.log("Number of found reviews: %d" % len(product['metadata']['reviews']))
            if 'mbc_list_url' in response.meta:
                meta = response.meta
                meta['_product'] = product
                self._append_request(response.meta['mbc_list_url'], self.parse_mbc_list, meta)
            else:
                if response.meta.get('matches_search', False):
                    source = "matches"
                else:
                    source = "search"
                self.log("Collecting items from %s. Identifier: %s, price: %s" %
                         (source, product['identifier'], str(product['price'])))
                self._collect(response.meta['collected_items'], product)

        for x in self._continue_requests(response):
            yield x

    def collect_price(self, hxs, response):
        soup = BeautifulSoup(response.body)
        try:
            soup_form = soup.find(id='handleBuy')
            price = soup_form.find('b', 'priceLarge')
            if not price:
                price = soup_form.find('span', 'priceLarge')
            if not price:
                price = soup_form.find('span', 'price')
            if not price:
                price = soup_form.find('span', 'pa_price')
            if price:
                price = self.extract_price(price.text)
            else:
                price = None
        except AttributeError:
            price = hxs.select('//div[@id="price"]//td[text()="Price:"]'
                               '/following-sibling::td/span/text()').extract()
            if not price:
                price = hxs.select('//span[@id="priceblock_saleprice"]/text()').extract()
            if not price:
                price = hxs.select('//span[@id="actualPriceValue"]/*[@class="priceLarge"]/text()').extract()
            if not price:
                price = hxs.select('//span[@id="priceblock_ourprice"]/text()').extract()

            if price:
                price = self.extract_price(price[0])
            else:
                price = None

        return price

    def _extract_review_date(self, review):
        '''
        :param review: review selector
        '''

        date = review.select(u'.//nobr/text()')[0].extract()
        if '.fr' in self.domain:
            months = {u'janvier':u'January',
                      u'février':u'February',
                      u'mars':u'March',
                      u'avril':u'April',
                      u'mai':u'May',
                      u'juin':u'June',
                      u'juillet':u'July',
                      u'août':u'August',
                      u'septembre':u'September',
                      u'octobre':u'October',
                      u'novembre':u'November',
                      u'décembre':u'December'}
            for french_month, month in months.iteritems():
                date = date.upper().replace(french_month.upper(), month.upper())
        return date

    def _extract_review_rating(self, review):
        '''
        :param review: review selector
        '''

        if '.fr' in self.domain:
            rating = review.select(u'.//text()').re(u'([\d\.]+) étoiles sur 5')[0]
        else:
            rating = review.select(u'.//text()').re(u'([\d\.]+) out of 5 stars')[0]
        return rating


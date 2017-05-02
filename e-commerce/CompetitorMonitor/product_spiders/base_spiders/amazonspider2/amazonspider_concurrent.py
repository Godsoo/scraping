# -*- coding: utf-8 -*-

import re
import csv
import json
import os.path
import pandas as pd
import itertools
from hashlib import md5
from decimal import Decimal
from datetime import datetime, date
from collections import defaultdict
from urllib import urlencode

try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider
from scrapy.exceptions import CloseSpider, DontCloseSpider
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy import log

from product_spiders.utils import extract_price2uk
from product_spiders.utils import read_json_lines_from_file_generator, get_matched_products_for_spider
from product_spiders.base_spiders.matcher import Matcher
from product_spiders.config import DATA_DIR
from scraper import AmazonScraper, AmazonUrlCreator, AmazonScraperProductDetailsException
from items import AmazonProductLoader, AmazonProduct
from items import ReviewLoader, Review
from utils import get_asin_from_identifier, safe_copy_meta
from captcha import get_captcha_from_url

MAX_SKU_LEN = 255


def load_cache(cache_filename):
    sellers = {}
    with open(cache_filename) as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                seller_id = row['identifier'].split(':')[2].strip()
                seller_name = row['dealer'].decode('utf-8')
                sellers[seller_id] = seller_name
            except IndexError:
                continue
    return sellers


def get_base_identifier(identifier):
    """
    >>> get_base_identifier("asd:qwe")
    'asd'
    >>> get_base_identifier(':asd:qwe')
    'asd'
    >>> get_base_identifier('asd')
    'asd'
    >>> get_base_identifier(':asd')
    'asd'
    >>> get_base_identifier(':asd:')
    'asd'
    >>> get_base_identifier(':')
    ':'
    >>> get_base_identifier('')
    ''
    """
    split = identifier.split(':')
    parts = [x for x in split if x.strip()]

    if not parts:
        return identifier

    real_identifier = parts[0]
    return real_identifier


def _filter_name(name):
    m = re.search(r"^new offers for", name, re.I)
    if m:
        found = m.group(0)
        res = name.replace(found, "")
        res = res.strip()
    else:
        res = name
    return res


def _filter_brand(brand):
    if len(brand) > 100:
        brand = brand[:97].strip() + '...'
    return brand


def _filter_item(new_item):
    # new_item = self._filter_reviews(new_item)
    if 'name' in new_item:
        new_item['name'] = _filter_name(new_item['name'])

    if 'brand' in new_item:
        new_item['brand'] = _filter_brand(new_item['brand'])
    return new_item


class BaseAmazonConcurrentSpider(BaseSpider):
    """
    Alternative version of base amazon spider.
    Can perform several searches concurrently.
    """
    concurrent_searches = 4

    # Use unique amazon identifier
    use_amazon_identifier = True

    SPIDER_TYPES = ['search', 'asins', 'asins_offers', 'category']
    # Spider type:
    # 'search' type - takes list of search terms and tries to search every one of them on amazon using amazon search
    # 'asins' type - takes list of ASINs and processes corresponding products right from product details pages
    # 'asins_offers' type - takes list of ASINs and processes corresponding products from offer listing pages
    # 'category' type - takes list of category URLs and extracts all products from them
    # Default: search
    type = 'search'

    # Spider category parsing type
    # True - takes all products information from products list
    # False - takes products information from product details, useful when for example setting model number
    #         as sku of product
    collect_products_from_list = True

    # Only products sold by Amazon
    amazon_direct = False
    # Collect products only from results list and grab the dealer of this product (buybox)
    only_buybox = False
    # Collect all product's dealers
    all_sellers = False
    # Collect product with lowest price. Checks all sellers. Works differently for different crawl types:
    # 1) search - collects one product:seller with lowest price per each search query
    # 2) asin - collects lowest seller price
    # 3) category - collects all products with all sellers
    # FIXME: fix for "category" type
    lowest_product_and_seller = False

    # Exclude following sellers from results
    exclude_sellers = []
    # Monitor  only the following sellers
    sellers = []

    lowest_seller_collect_dealer_identifier = True

    # should "fulfilled by amazon" flag be added to identifier
    # sometimes the same seller sells product twice: one with its own delivery and another fulfilled by amazon
    # makes sense only when collecting seller identifier
    fulfilled_by_amazon_to_identifier = False

    # collect model as sku
    model_as_sku = False

    # collect reviews for products
    collect_reviews = False
    # Collect reviews once per product
    # meaning that if dealers are being collected, only one of products will have reviews)
    reviews_once_per_product_without_dealer = True
    # predefined date format for review
    review_date_format = u'%d/%m/%Y'
    # Collect only new reviews (checks with previous crawl)
    reviews_only_new = True
    # collect reviews only for matched products
    reviews_only_matched = True
    # Inc selector of review: useful to post-processing of that to add data
    reviews_inc_selector = False
    # only collect reviews from Verified Purchase
    reviews_only_verified = False
    # collect information about author
    reviews_collect_author = False
    reviews_collect_author_location = False


    # HACK: fix to issue with reviews, caused by bug in reviews updater, which made spider save only new reviews
    # only needed for spiders collecting only new reviews
    _hack_fix_related_to_bug_18_02_to_14_03 = True
    _hack_fix_related_to_bug_with_emtpy_reviews_may_june = True
    # issue with "only new" reviews
    _hack_fix_to_bug_only_new_reviews_2015_06_04 = True

    # Parse options from product page
    parse_options = False
    # Collect only colour options (useful for clothes/shoes)
    options_only_color = False

    # Collect all products even without dealer
    collect_products_with_no_dealer = False

    # if it's mandatory to collect dealer or not
    # when not mandatory spider will collect products from product list when possible
    dealer_is_mandatory = True

    # if product not matched when on products list - go to product details page to collect model
    try_match_product_details_if_product_list_not_matches = False

    # Should the spider retry or not
    do_retry = True
    # retry counter limit
    max_retry_count = 50
    # pause in seconds between retries
    # retry_sleep = 10

    # # MBC list specific options
    # Collect New products
    collect_new_products = True
    # Collect Used products
    collect_used_products = True
    # # END

    # # search type specific options
    # search in specific category
    # this is NOT the name of category, it's the "keyword" name of category,
    # which can be found in url in parameter "url" after "search-alias=" text
    # if set to None will search across all categories
    search_category = None
    # # END

    # search in specific sub-category
    # It is a code that can be found in the url as the parameter "node="
    # if set to None will search across all sub-categories
    search_node = None

    # Max search result pages to crawl
    max_pages = None

    # Filename for file with brand and sellers cache
    cache_filename = None

    # try suggested searches when main search fails
    try_suggested = True

    # put semicolon in front of identifier
    semicolon_in_identifier = True

    deduplicate_identifiers = True

    # scraper class
    scraper_class = AmazonScraper

    # TODO: use cache for brands

    # auxilary - number of pages amazon shows maximum for category
    _max_pages = 400

    # use UserAgentMiddleware to rotate agents automatically - should reduce number of antibot blockings
    rotate_agent = True

    # When type is "search" and a search does not found results then it's going to retry it at the end of the crawl.
    retry_search_not_found = False

    # Scrape ordered categories from product details, disabled by default as it can be
    # unwanted behaviour for existing spiders
    scrape_categories_from_product_details = False
    use_previous_crawl_cache = False

    retry_vendor_name = True

    map_retry_blocked = True

    def __init__(self, *args, **kwargs):
        self.log("[AMAZON] Initializing amazon spider")

        self.errors = []

        # initializing domain before calling super method
        # so bigsitemethod will not complain about missing allowed_domains
        if not hasattr(self, 'domain'):
            msg = "[AMAZON] Attribute `domain` should be set. Using default 'amazon.com'"
            self.log(msg, level=log.ERROR)
            self.errors.append(msg)
            self.domain = 'amazon.com'
        self.allowed_domains = [self.domain]

        super(BaseAmazonConcurrentSpider, self).__init__(*args, **kwargs)

        dispatcher.connect(self.process_next_step, signals.spider_idle)
        dispatcher.connect(self.spider_opened, signals.spider_opened)
        dispatcher.connect(self.spider_stats_closing, signals.stats_spider_closing)

        self.items_not_found_callback = None

        self.max_retry_search_not_found_count = 10

        if self.lowest_product_and_seller:
            self._collect = self._collect_lowest_price
        else:
            self._collect = self._collect_all
        # if self.all_sellers:
        #     self._collect = self._collect_all
        # else:
        #     self._collect = self._collect_lowest_price

        self.search_generator = None
        self.asins_generator = None
        self.category_url_generator = None

        self.collected_items = {}
        self.collected_reviews = {}

        # all these are needed to properly process search retrying
        # first 4 dicts has "search_id" as keys
        self.retry_search_count = {}
        self.processed_items = {}
        self.current_search = {}
        self.current_search_item = {}
        # this is a list of tuples (search_string, search_item) of searches to retry
        self.searches_to_retry = []

        self.reviews_collected_for = {}

        self.prev_crawl_reviews = {}

        self.scraper = self.scraper_class()
        self.matcher = Matcher()

        self.finished = False

        self.sellers_cache = {}

        if [self.amazon_direct, self.only_buybox, self.all_sellers, self.lowest_product_and_seller].count(True) != 1:
            msg = "[AMAZON] Should be one of: amazon_direct, only_buybox, all_sellers, lowest_seller"
            self.log(msg, level=log.ERROR)
            self.errors.append(msg)

        if not self._is_spider_type_valid(self.type):
            msg = "[AMAZON] Type is incorrect: %s. " \
                  "A string or list of strings with value one of: %s" % \
                  (self.type, self.SPIDER_TYPES)
            self.log(msg, level=log.ERROR)
            self.errors.append(msg)

        if isinstance(self.type, list):
            self.full_type = self.type
            self.type = None
        else:
            self.full_type = [self.type]
            self.type = None
        self._cycle_to_next_type()

        if self.cache_filename:
            self.sellers_cache.update(load_cache(self.cache_filename))

        # additional stats
        self.antibot_blocked_count = 0
        self.antibot_blocked_fully_urls = defaultdict(int)

        self.parsed_count = defaultdict(int)

        self.matched_product_asins = set()

        self.previous_data_df = None

        if self.scrape_categories_from_product_details:
            self.use_previous_crawl_cache = True

        # checking if options found
        # will output alert if spider is set to parse options but no options found for products
        self.options_found = False
        self.products_with_options = 0

        # authors and author locations cache
        self.review_authors = {}
        self.review_author_locations = {}

    @classmethod
    def _is_spider_type_valid(cls, spider_type):
        if isinstance(spider_type, basestring):
            return cls._is_type_valid(spider_type)
        elif isinstance(spider_type, list):

            return all([cls._is_type_valid(t) for t in spider_type]) and len(spider_type) == len(set(spider_type))
        else:
            raise TypeError("Wrong type for `type` attribute: %s" % type(spider_type))

    @classmethod
    def _is_type_valid(cls, t):
        return t in cls.SPIDER_TYPES

    def _prev_metadata_generator(self, all_meta_file):
        if all_meta_file.endswith('.json-lines'):
            file_format = 'json-lines'
        elif all_meta_file.endswith('.json'):
            file_format = 'json'
        else:
            self.log("[Amazon] Unknown format of meta file: %s. Using default JSON")
            file_format = 'json'
        if file_format == 'json':
            with open(all_meta_file) as f:
                data = f.read()
                if len(data) > 0:
                    for meta in json.loads(data):
                        yield meta
        elif file_format == 'json-lines':
            for meta in read_json_lines_from_file_generator(all_meta_file):
                yield meta
        else:
            assert False, "File format is either 'json' or 'json-lines'"

    def _load_prev_reviews_dates(self, all_meta_file):
        prev_crawl_reviews = {}
        if self._hack_fix_related_to_bug_18_02_to_14_03:
            # check date is earlier than 27.03.2015 then do not load previous reviews
            threshold_date = date(2015, 3, 27)
            if date.today() < threshold_date:
                return prev_crawl_reviews

        if self._hack_fix_to_bug_only_new_reviews_2015_06_04:
            threshold_date = date(2015, 6, 7)
            if date.today() < threshold_date:
                return prev_crawl_reviews

        if self._hack_fix_related_to_bug_with_emtpy_reviews_may_june:
            # check date is earlier than 08.06.2015 then do load previous reviews till mid April
            threshold_date = date(2015, 8, 05)
            if date.today() < threshold_date:
                review_date_threshold = date(2015, 04, 15)
                for meta in self._prev_metadata_generator(all_meta_file):
                    newest_review_date = None
                    for review in meta['metadata'].get('reviews', []):
                        try:
                            review_date = datetime.strptime(review['date'], self.review_date_format).date()
                        except ValueError:
                            continue
                        else:
                            if review_date > review_date_threshold:
                                continue
                            if newest_review_date is None or review_date > newest_review_date:
                                newest_review_date = review_date
                    if newest_review_date:
                        identifier = meta['identifier']
                        real_identifier = get_base_identifier(identifier)
                        prev_crawl_reviews[real_identifier] = newest_review_date

        for meta in self._prev_metadata_generator(all_meta_file):
            newest_review_date = None
            for review in meta['metadata'].get('reviews', []):
                try:
                    review_date = datetime.strptime(review['date'], self.review_date_format).date()
                except (ValueError, TypeError, KeyError):
                    continue
                else:
                    if newest_review_date is None or review_date > newest_review_date:
                        newest_review_date = review_date
            if newest_review_date:
                identifier = meta['identifier']
                real_identifier = get_base_identifier(identifier)
                prev_crawl_reviews[real_identifier] = newest_review_date
        return prev_crawl_reviews

    def spider_opened(self, spider):
        self.log("[AMAZON] Spider opened start")
        if spider.name == self.name:
            if self.use_previous_crawl_cache:
                if hasattr(self, 'prev_crawl_id'):
                    filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
                    if os.path.exists(filename):
                        self.log('[AMAZON] Using previous crawl data as cache')
                        self.previous_data_df = pd.read_csv(filename, dtype=pd.np.str, encoding='utf-8')

            if self.collect_reviews:
                reviews_attrs = []
                if self.reviews_only_new:
                    reviews_attrs.append('new')
                if self.reviews_only_matched:
                    reviews_attrs.append('matched')
                if not reviews_attrs:
                    reviews_attrs.append('all')
                self.log("[AMAZON] Collect %s reviews" % " and ".join(reviews_attrs))

            # if reviews enabled - load products with reviews
            if self.collect_reviews and self.reviews_only_new:
                all_meta_file = self._amazon_get_prev_crawl_meta_file()
                if all_meta_file:
                    self.log("[AMAZON] Loading previous reviews from file: %s" % all_meta_file)
                    self.prev_crawl_reviews = self._load_prev_reviews_dates(all_meta_file)
        # there is no point in downloading matches asynchronously, because we need them before doing any request
        # so downloading matches using blocking request
        if self.collect_reviews and self.reviews_only_matched:
            self.log('[AMAZON] Collecting matched products')
            try:
                matched_products = get_matched_products_for_spider(spider)
            except (AttributeError, KeyError) as e:
                self.log('[AMAZON] Error when getting matched products for spider: %s' % e.message)
            else:
                self.log('[AMAZON] Got %d products' % len(matched_products))
                for prod in matched_products:
                    asin = get_asin_from_identifier(prod['identifier'])
                    self.matched_product_asins.add(asin)
        self.log("[AMAZON] Spider opened")

    def spider_stats_closing(self, spider, reason):
        stats = self.crawler.stats
        for parsed_func, parsed_count in self.parsed_count.items():
            key = 'parsed/' + parsed_func
            stats.set_value(key, parsed_count, self)
        if self.parse_options:
            stats.set_value('parsed_products_with_options', self.products_with_options)
            if not self.options_found:
                if not hasattr(spider, 'full_run') or spider.full_run:
                    self.errors.append('Spider is set to parse options but no options scraped')

    # Only if Proxy Service enabled
    def proxy_service_check_response(self, response):
        res = self.scraper.antibot_protection_raised(response.body_as_unicode())
        if res:
            self.log("[AMAZON] Antibot protection detected: %s" % response.url)
        return res

    def _amazon_get_prev_crawl_meta_filename(self, type='json'):
        if hasattr(self, 'prev_crawl_id'):
            filename = 'data/meta/%s_meta.%s' % (self.prev_crawl_id, type)
            return filename
        return None

    def _amazon_get_prev_crawl_meta_file(self):
        filename = self._amazon_get_prev_crawl_meta_filename(type='json')
        if filename is None:
            return None
        # check for existence
        if os.path.exists(filename):
            return filename
        filename = self._amazon_get_prev_crawl_meta_filename(type='json-lines')
        if filename is None:
            return None
        if os.path.exists(filename):
            return filename
        return None

    def _collect_all(self, new_item, search_id):
        """
        Collects all products
        """
        new_item = _filter_item(new_item)
        for i, item in enumerate(self.collected_items.get(search_id, [])):
            if new_item['identifier'] == item['identifier']:
                if new_item['price'] != item['price']:
                    self.log('[AMAZON] Product %s has different prices %s and %s' % (
                        new_item['identifier'], new_item['price'], item['price']))
                    item['price'] = min(item['price'], new_item['price'])
                return False
        self.collected_items[search_id].append(new_item)
        return True

    def _collect_lowest_price(self, new_item, search_id):
        """ Keeps only product with the lowest price """
        new_item = _filter_item(new_item)
        if self.collected_items.get(search_id):
            i = self.collected_items[search_id][0]
            if Decimal(i['price']) > Decimal(new_item['price']):
                self.collected_items[search_id][0] = new_item
        else:
            self.collected_items[search_id].append(new_item)

    def _collect_best_match(self, new_item, search):
        """ Keeps only product with the lowest price """
        new_item = _filter_item(new_item)
        if self.collected_items:
            i = self.collected_items[0]
            match_threshold = self.matcher.match_ratio(search, i['name'], None)
            if self.matcher.match_ratio(search, new_item['name'], None) > match_threshold:
                self.collected_items[0] = new_item
        else:
            self.collected_items.append(new_item)

    def _collect_amazon_direct(self, product, meta, search_id):
        self._collect_all(product, search_id)

    def _collect_buybox(self, product, meta, search_id):
        self._collect_all(product, search_id)

    def _collect_review(self, identifier, review):
        identifier = get_base_identifier(identifier)
        if self.reviews_only_verified and not review['verified']:
            return
        res = self.construct_review(review)

        if identifier in self.collected_reviews:
            self.collected_reviews[identifier].append(res)
        else:
            self.collected_reviews[identifier] = [res]

        self.log("[AMAZON] Added review for %s, total reviews: %d" % (identifier,
                                                                      len(self.collected_reviews[identifier])))

    def _collect_reviews(self, identifier, reviews):
        for review in reviews:
            self._collect_review(identifier, review)

    def _seller_ok(self, seller):
        test_seller = seller
        if test_seller.startswith('AM - '):
            test_seller = test_seller[5:].strip()
        for exclude in self.exclude_sellers:
            if test_seller.lower() == exclude.lower():
                self.log('[AMAZON] Excluding seller name => %s' % seller)
                return False

        if self.sellers:
            for monitor_seller in self.sellers:
                if test_seller.lower() == monitor_seller.lower():
                    return True
            self.log('[AMAZON] Excluding seller name => %s' % seller)
            return False
        return True

    def get_search_query_generator(self):
        """
        Yields search data. Search item should have fields 'name', 'price'
        :return: generator of tuples (search_string, search_item)
        """
        raise NotImplementedError("Spider should implement method `get_search_query_generator`!")

    def get_asins_generator(self):
        """
        Yields ASINs one by one. Should be tuple with two values: asin and SKU. SKU is then set to all products
        found for this ASIN. If there is no SKU to provided it should be None
        """
        raise NotImplementedError("Spider should implement method `get_asins_generator`!")

    def get_category_url_generator(self):
        """
        Yields category urls one by one
        """
        raise NotImplementedError("Spider should implement method `get_category_url_generator`!")

    def get_next_search_request(self, callback=None):
        # search iterator: first process searches to retry, then new searches
        search_iterator = itertools.chain(self.searches_to_retry, self.search_generator)

        for current_search_no, (search_string, search_item) in enumerate(search_iterator):
            if search_string is None:
                self.log('[AMAZON] Dummy request')
                url = "file:///etc/hosts"
                yield Request(url, dont_filter=True, callback=self.dummy_callback)
            else:
                search_id = md5(search_string).hexdigest()
                self.collected_items[search_id] = []
                if search_id not in self.retry_search_count:
                    self.retry_search_count[search_id] = 0
                self.processed_items[search_id] = False
                self.current_search[search_id] = search_string
                self.current_search_item[search_id] = search_item

                if self.retry_search_count.get(search_id, 0) > 0:
                    self.log('[AMAZON] Searching again for [%s] - %s' %
                             (search_string, self.retry_search_count[search_id]))
                else:
                    self.log('[AMAZON] Searching for [%s]' % search_string)

                url = AmazonUrlCreator.build_search_url(
                    self.domain, search_string, self.amazon_direct,
                    search_alias=self.search_category, search_node=self.search_node)

                if callback is None:
                    callback = self.parse_product_list

                yield Request(
                    url,
                    meta={'search_string': search_string,
                          'search_item': search_item,
                          'search_id': search_id,
                          'retry_search_count': self.retry_search_count[search_id]},
                    dont_filter=True, callback=callback)
            # Important! This check should be at the end of the cycle
            # as otherwise we will get next item from generator and discard it because of "break"
            if current_search_no + 1 >= self.concurrent_searches:
                break

    def get_next_asin_request(self, callback=None):
        for current_search_no, (asin, sku) in enumerate(self.asins_generator):
            self.log('[AMAZON] Loading asin [%s]' % asin)

            search_item = {'identifier': asin, 'asin': asin, 'sku': sku}
            self.collected_items[asin] = []

            url = AmazonUrlCreator.build_url_from_asin(self.domain, asin)

            if callback is None:
                callback = self.parse_product

            yield Request(
                url,
                meta={'search_item': search_item,
                      'search_id': asin},
                dont_filter=True, callback=callback)
            # Important! This check should be at the end of the cycle
            # as otherwise we will get next item from generator and discard it because of "break"
            if current_search_no + 1 >= self.concurrent_searches:
                return

    def get_next_asin_offers_request(self, callback=None):
        for current_search_no, (asin, product_sku) in enumerate(self.asins_generator):
            self.log('[AMAZON] Loading asin [%s]' % asin)

            if isinstance(product_sku, dict):
                product_sku['asin'] = asin
                search_item = product_sku
            else:
                search_item = {'identifier': asin, 'asin': asin, 'sku': product_sku}

            self.collected_items[asin] = []

            url = AmazonUrlCreator.build_offer_listing_new_url_from_asin(self.domain, asin)

            if callback is None:
                callback = self.parse_mbc_list

            yield Request(
                url,
                meta={'search_item': search_item,
                      'search_id': asin},
                dont_filter=True, callback=callback)
            # Important! This check should be at the end of the cycle
            # as otherwise we will get next item from generator and discard it because of "break"
            if current_search_no + 1 >= self.concurrent_searches:
                return

    def get_next_category_request(self, callback=None):
        for url, category_name in self.category_url_generator:
            self.log('[AMAZON] Loading category url [%s]' % url)

            if callback is None:
                callback = self.parse_product_list

                yield Request(url, dont_filter=True, callback=callback, meta={'category': category_name})

    def start_requests(self):
        """
        The method assumes the spider is using search.
        To get items to search spider must have `get_search_query_generator` function implemented, which must be
        generator returning tuple of form (search_string, search_item). This is not finally decided yet
        """
        self.log("[AMAZON] start_requests")
        if self.type == 'search':
            self.search_generator = self.get_search_query_generator()
            for req in self.get_next_search_request():
                yield req
        elif self.type == 'asins':
            self.asins_generator = self.get_asins_generator()
            for req in self.get_next_asin_request():
                yield req
        elif self.type == 'asins_offers':
            self.asins_generator = self.get_asins_generator()
            for req in self.get_next_asin_offers_request():
                yield req
        elif self.type == 'category':
            self.category_url_generator = self.get_category_url_generator()
            for req in self.get_next_category_request():
                yield req
        else:
            self.errors.append("Wrong spider type: %s" % self.type)

    def _cycle_to_next_type(self):
        if len(self.full_type):
            self.type = self.full_type.pop(0)
            return self.type
        else:
            self.type = None
            return None

    def process_next_step(self, spider):
        if self.collected_items:
            self.log("[AMAZON] Spider idle. Processing collected products")
            r = Request(
                "file:///etc/hosts",
                dont_filter=True,
                meta={'dont_redirect': True,
                      'handle_httpstatus_all': True},
                callback=lambda response: self.process_collected_products()
            )
            self.crawler.engine.crawl(r, self)
        else:
            for search_id, has_processed_items in self.processed_items.items():
                if not has_processed_items:
                    if self.items_not_found_callback:
                        self.items_not_found_callback(self.current_search[search_id], self.current_search_item[search_id])
                    if self.retry_search_not_found and self.max_retry_search_not_found_count > 0:
                        self.retry_search_count[search_id] += 1
                        if self.retry_search_count[search_id] < self.max_retry_search_not_found_count:
                            self.searches_to_retry.append((self.current_search[search_id], self.current_search_item[search_id]))
            if self.type == 'search':
                self.log("[AMAZON] Spider idle. Processing next search")
                self.process_next_search()
            elif self.type == 'asins':
                self.log("[AMAZON] Spider idle. Processing next ASIN")
                self.process_next_asin()
            elif self.type == 'asins_offers':
                self.log("[AMAZON] Spider idle. Processing next ASIN")
                self.process_next_asin_offers()
            elif self.type == 'category':
                self.log("[AMAZON] Spider idle. Processing next category")
                self.process_next_category()
            else:
                self.log("[AMAZON] Wrong spider type: %s" % self.type)
        if not self.finished:
            raise DontCloseSpider
        else:
            res = self._cycle_to_next_type()
            if res:
                self.finished = False
                requests = self.start_requests()
                for r in requests:
                    self.crawler.engine.crawl(r, self)
                raise DontCloseSpider
            else:
                if len(self.antibot_blocked_fully_urls) > 0:
                    for func_name, blocked_count in self.antibot_blocked_fully_urls.items():
                        msg = "'%s' function blocked on %d urls" % (func_name, blocked_count)
                        self.log(msg)
                        self.errors.append(msg)
                elif self.antibot_blocked_count > 0:
                    msg = "Spider blocked by antibot protection system %d times. " \
                          "But was able to crawl all URLs on retry" % self.antibot_blocked_count
                    self.log(msg)

    def process_collected_products(self):
        for search_id, collected_items in self.collected_items.items():
            self.log("[[TESTING]] Items to collects: %d" % len(collected_items))
            count = 0
            for item in collected_items:
                real_identifier = get_base_identifier(item['identifier'])

                if real_identifier not in self.collected_reviews and item['identifier'] in self.collected_reviews:
                    real_identifier = item['identifier']

                reviews = self.collected_reviews.get(real_identifier, None)
                if reviews:
                    if 'metadata' in item:
                        item['metadata']['reviews'] = reviews
                    else:
                        item['metadata'] = {
                            'reviews': reviews
                        }
                    if self.reviews_once_per_product_without_dealer:
                        del(self.collected_reviews[real_identifier])
                yield item
                count += 1
            self.log("[[TESTING]] Collected items: %d" % count)
            self.processed_items[search_id] = True

        self.collected_items = {}

    def process_next_search(self):
        """
        This method is executed when spider is idle. It launches search for next search item,
        if there is no more items to search it does nothing
        """
        requests = list(self.get_next_search_request())

        if not requests:
            self.finished = True
            self.log("[AMAZON] Spider finished")
            return
        else:
            for r in requests:
                self.log("[AMAZON] Process_next_search: %s" % r.meta['search_string'])
                self.crawler.engine.crawl(r, self)

    def process_next_asin(self):
        """
        This method is executed when spider is idle. It launches crawl for next ASIN,
        if there is no more ASINs it does nothing
        """
        requests = list(self.get_next_asin_request())
        if not requests:
            self.finished = True
            self.log("[AMAZON] Spider finished")
            return
        else:
            for r in requests:
                self.log("[AMAZON] Process_next_asin: %s" % r.meta['search_item']['asin'])
                self.crawler.engine.crawl(r, self)

    def process_next_asin_offers(self):
        """
        This method is executed when spider is idle. It launches crawl for next ASIN,
        if there is no more ASINs it does nothing
        """
        requests = list(self.get_next_asin_offers_request())
        if not requests:
            self.finished = True
            self.log("[AMAZON] Spider finished")
            return
        else:
            for r in requests:
                self.log("[AMAZON] Process_next_asin: %s" % r.meta['search_item']['asin'])
                self.crawler.engine.crawl(r, self)

    def process_next_category(self):
        """
        This method is executed when spider is idle. It launches crawl for next category url,
        if there is no more category urls it does nothing
        """
        requests = list(self.get_next_category_request())
        if not requests:
            self.finished = True
            self.log("[AMAZON] Spider finished")
            return
        else:
            for r in requests:
                self.log("[AMAZON] Process_next_category: %s" % r.url)
                self.crawler.engine.crawl(r, self)

    def match(self, meta, search_item, found_item):
        """
        Should check if found item is match for search item
        :rtype Boolean
        :return True if found item is a match, False otherwise
        """
        if self.type == 'asins':
            return True
        elif self.type == 'category':
            return True
        elif self.type == 'search':
            raise NotImplementedError("Spider should implement method `match`!")
        else:
            raise CloseSpider("Wrong spider type: %s" % self.type)

    def basic_match(self, meta, search_item, found_item):
        return self.match(meta, search_item, found_item)

    def match_price(self, search_item, new_item, price_diff=0.5):
        """ Checks price variation """
        if not search_item['price']:
            return True
        search_price = Decimal(search_item['price'])
        diff = Decimal(search_price) * Decimal(price_diff)
        if isinstance(new_item['price'], tuple):
            matches = any([search_price - diff <= Decimal(x) <= search_price + diff for x in new_item['price']])
        else:
            matches = search_price - diff <= Decimal(new_item['price']) <= search_price + diff
        if not matches:
            self.log('[AMAZON] Item price is too different from %s, reject %s' % (search_price, new_item))
        return matches

    def match_name(self, search_item, new_item, match_threshold=90, important_words=None):
        r = self.matcher.match_ratio(search_item['name'], new_item['name'], important_words)
        return r >= match_threshold

    def match_text(self, text, new_item, match_threshold=90, important_words=None):
        r = self.matcher.match_ratio(text, new_item['name'], important_words)
        return r >= match_threshold

    def transform_price(self, price):
        return price

    def construct_product(self, item, meta=None, use_seller_id_in_identifier=None):
        """
        Constructs `Product` instance from dict
        """
        if use_seller_id_in_identifier is None:
            if self.all_sellers:
                use_seller_id_in_identifier = True
            else:
                use_seller_id_in_identifier = False

        if meta and 'item' in meta:
            search_item = meta['item']
        elif meta and 'search_item' in meta:
            search_item = meta['search_item']
        else:
            search_item = {}

        loader = AmazonProductLoader(item=AmazonProduct(), response=HtmlResponse(''))
        necessary_fields = ['name']
        optional_fields = ['sku', 'image_url', 'brand', 'stock']
        fields_from_search_item = ['sku', 'category', 'brand', 'identifier']

        synonym_fields = {
            'vendor': 'dealer',
        }

        identifier = item['identifier'] if self.use_amazon_identifier else search_item.get('identifier')
        if self.semicolon_in_identifier and \
                identifier and \
                self.use_amazon_identifier and \
                not identifier.startswith(':'):
            identifier = ':' + identifier

        if identifier and use_seller_id_in_identifier and item.get('seller_identifier'):
            identifier += ':' + item['seller_identifier']
            if self.fulfilled_by_amazon_to_identifier and 'fulfilled_by_amazon' in item:
                flag = '1' if item['fulfilled_by_amazon'] else "0"
                identifier += ':' + flag

        loader.add_value('identifier', identifier)

        for field in necessary_fields:
            loader.add_value(field, item[field])

        if item['price'] is not None:
            try:
                if type(item['price']) == tuple or type(item['price']) == list:
                    item['price'] = item['price'][0]
                price = extract_price2uk(item['price']) if not isinstance(item['price'], Decimal) else item['price']
            except Exception, e:
                self.log('ERROR: extracting price => PRICE: %s' % repr(item['price']))
                raise e
        else:
            price = Decimal('0')
        price = self.transform_price(price)
        loader.add_value('price', price)

        if item.get('asin') and item.get('seller_identifier'):
            loader.add_value(
                'url',
                AmazonUrlCreator.build_url_from_asin_and_dealer_id(
                    self.domain,
                    item['asin'],
                    item['seller_identifier']
                )
            )
        elif item.get('asin'):
            loader.add_value(
                'url',
                AmazonUrlCreator.build_url_from_asin(
                    self.domain,
                    item['asin']
                )
            )
        elif self.use_amazon_identifier:
            loader.add_value(
                'url',
                AmazonUrlCreator.build_url_from_asin(
                    self.domain,
                    item['identifier']
                )
            )
        elif item.get('url'):
            loader.add_value('url', item['url'])

        # take sku from model if configured to do so
        if item.get('model') and self.model_as_sku:
            model = item['model']
            if len(model) > MAX_SKU_LEN:
                model = model[:252] + '...'

            loader.add_value('sku', model)

        # pick search item
        # BSM simple run
        for field in optional_fields:
            if field in item and item[field]:
                loader.add_value(field, item[field])
            elif field in fields_from_search_item and search_item and field in search_item:
                if not loader.get_output_value(field):
                    loader.add_value(field, search_item[field])

        # get category from "categories" scraped by Scraper, only if enabled for spider
        if self.scrape_categories_from_product_details:
            item['category'] = item['categories']

        # category
        category = None
        if 'category' in item and item['category']:
            category = item['category']
        elif 'category' in fields_from_search_item and search_item and 'category' in search_item:
            category = search_item['category']
        elif self.type == 'category':
            if meta and meta.get('category'):
                category = meta['category']

        if category:
            if isinstance(category, list):
                for cat in category:
                    loader.add_value('category', cat)
            else:
                loader.add_value('category', category)
        else:
            loader.add_value('category', '')

        if item.get('shipping_cost', None):
            loader.add_value(
                'shipping_cost',
                extract_price2uk(item['shipping_cost'])
                if not isinstance(item['shipping_cost'], Decimal) else item['shipping_cost']
            )

        for synonym_field, field in synonym_fields.items():
            if synonym_field in item:
                value = item[synonym_field]
                loader.add_value(field, value)

        if item.get('unavailable'):
            loader.add_value('stock', 0)

        # if there is a seller identifier then there should be dealer
        if item.get('seller_identifier') and use_seller_id_in_identifier and not loader.get_output_value('dealer'):
            self.errors.append("Product with seller identifier but no dealer: %s" % loader.get_output_value('url'))

        product = loader.load_item()
        return product

    def construct_review(self, review):
        review_date = review['date']
        if self.review_date_format:
            review_date = review_date.strftime(self.review_date_format)
        loader = ReviewLoader(item=Review(), response=HtmlResponse(''))
        loader.add_value('date', review_date)
        loader.add_value('rating', review['rating'])
        loader.add_value('url', review['url'])
        loader.add_value('review_id', review['identifier'])
        if not review['identifier']:
            self.errors.append("Couldn't scrape review_id for review: %s" % review['url'])
        text = review['full_text'].strip()
        if not text.endswith('.'):
            text += '.'
        if self.reviews_collect_author:
            loader.add_value('author', review['author'])
            if review['author']:
                text += " by " + review['author']
        if self.reviews_collect_author_location:
            location = review['author_location']
            if location:
                text += " from " + location
            loader.add_value('author_location', location)

        loader.add_value('full_text', text)
        return loader.load_item()

    def retry_download(self, url, metadata, callback, blocked=False, headers=None, response=None):
        no_try = metadata.get('try', 1)
        self.log("[AMAZON] Try %d. Retrying to download %s" %
                 (no_try, url))
        if no_try < self.max_retry_count:
            meta = safe_copy_meta(metadata)
            meta['try'] = no_try + 1
            meta['renew_tor'] = True
            meta['recache'] = True
            meta['renew_user-agent'] = True
            # time.sleep(self.retry_sleep)
            # Proxy Server support to exclude blocked proxy
            if blocked and headers and ('X-Ps-Pid' in headers):
                return Request(
                    url,
                    callback=callback,
                    meta=meta,
                    headers={'X-PSExclude-PID': headers['X-Ps-Pid']},
                    dont_filter=True,
                    errback=lambda failure: self.retry_download(url, meta, callback, response=response)
                )
            else:
                return Request(
                    url,
                    callback=callback,
                    meta=meta,
                    dont_filter=True,
                    errback=lambda failure: self.retry_download(url, meta, callback, response=response)
                )

    def should_do_retry(self, response):
        if not self.do_retry:
            return False

        no_try = response.meta.get('try', 1)
        if no_try < self.max_retry_count:
            return True

        return False

    def need_details_page(self, item):
        """
        Checks if we need to go to the product details page
        """
        result = False
        if self.model_as_sku or self.parse_options:
            result = True
        elif self.scrape_categories_from_product_details:
            result = True
            if self.use_previous_crawl_cache and self.previous_data_df is not None:
                self.log('[AMAZON] Check if identifier is in previous crawl data')
                # Check if identifier is in previous crawl data
                # If so then just copy the category from there
                # If isn't in then it will enter to product page
                item_identifier = item['identifier']
                if self.amazon_direct:
                    item_identifier = ':' + item_identifier
                products_found = self.previous_data_df[self.previous_data_df['identifier'] == item_identifier]
                if not products_found.empty:
                    category = dict(products_found.iloc[0]).get('category', '')
                    brand = dict(products_found.iloc[0]).get('brand', '')
                    if category:
                        self.log('[AMAZON] Collected category from previous crawl for product with identifier %s' % item_identifier)
                        item['categories'] = category.split(' > ')
                        result = False
                        if brand:
                            item['brand'] = brand


        if result:
            self.log('[AMAZON] Parse product page for product with identifier %s' % item['identifier'])
        return result

    def should_collect_reviews(self, item):
        if not self.collect_reviews:
            return False
        if self.reviews_only_matched and item.get('asin') not in self.matched_product_asins:
            return False
        if not item.get('reviews_url'):
            return False
        return True

    def _process_product_list_item_amazon_direct(self, response, item):
        """
        Must yield value of matched_any as last element
        """
        matched_any = False
        match = self.match(response.meta, response.meta['search_item'], item)
        if match:
            matched_any = True
            if self.need_details_page(item):
                # go to product details page to parse options
                new_meta = safe_copy_meta(response.meta)
                new_meta['check_match'] = False
                if self.type == 'search':
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': response.meta['search_item'],
                    })
                new_headers = response.headers.copy()
                new_headers['Referer'] = ''
                yield Request(
                    item['url'],
                    callback=self.parse_product,
                    meta=new_meta,
                    headers=new_headers
                )
            else:
                # amazon direct spider should already filter search results for only amazon products
                # so just setting dealer to Amazon and collecting
                product = self.construct_product(item, meta=response.meta)
                product['dealer'] = 'Amazon'

                # collect product
                if self.type == 'category' and not self.should_collect_reviews(item):
                    # yield directly only if category type AND not collecting reviews
                    self.log("[AMAZON] Scraping product %s (%s) from url %s" %
                             (product['name'], product['identifier'], response.url))
                    yield product
                else:
                    self.log("[AMAZON] Collecting product %s (%s) from url %s" %
                             (product['name'], product['identifier'], response.url))
                    self._collect_amazon_direct(product, response.meta, response.meta['search_id'])
                if self.should_collect_reviews(item):
                    # yield reviews parse
                    new_meta = safe_copy_meta(response.meta)
                    new_meta['found_item'] = item
                    if self.type == 'search':
                        new_meta.update({
                            'search_string': response.meta['search_string'],
                            'search_item': response.meta['search_item'],
                        })
                    yield Request(
                        item['reviews_url'],
                        callback=self.parse_reviews,
                        meta=new_meta
                    )
        elif self.try_match_product_details_if_product_list_not_matches:
            # go to product details page to extract SKU and try matching again
            new_meta = safe_copy_meta(response.meta)
            new_meta.update({
                'search_string': response.meta['search_string'],
                'search_item': response.meta['search_item'],
                'check_match': True,
            })
            new_headers = response.headers.copy()
            new_headers['Referer'] = ''
            yield Request(
                item['url'],
                callback=self.parse_product,
                meta=new_meta,
                headers=new_headers
            )
        yield matched_any

    def _process_product_list_item_buybox(self, response, item):
        """
        Must yield value of matched_any as last element
        """
        matched_any = False
        match = self.match(response.meta, response.meta['search_item'], item)
        if match:
            matched_any = True
            if self.need_details_page(item) or self.dealer_is_mandatory:
                new_meta = safe_copy_meta(response.meta)
                new_meta['check_match'] = False
                if self.type == 'search':
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': response.meta['search_item'],
                    })
                new_headers = response.headers.copy()
                new_headers['Referer'] = ''
                yield Request(
                    item['url'],
                    callback=self.parse_product,
                    meta=new_meta,
                    headers=new_headers
                )
            else:
                product = self.construct_product(item, meta=response.meta)
                product['dealer'] = ''

                # collect product
                if self.type == 'category' and not self.should_collect_reviews(item):
                    # yield directly only if category type AND not collecting reviews
                    self.log("[AMAZON] Scraping product %s (%s) from url %s" %
                             (product['name'], product['identifier'], response.url))
                    yield product
                else:
                    self.log("[AMAZON] Collecting product %s (%s) from url %s" %
                             (product['name'], product['identifier'], response.url))
                    self._collect_buybox(product, response.meta, response.meta['search_id'])
                if self.should_collect_reviews(item):
                    # yield reviews parse
                    new_meta = safe_copy_meta(response.meta)
                    new_meta['found_item'] = item
                    if self.type == 'search':
                        new_meta.update({
                            'search_string': response.meta['search_string'],
                            'search_item': response.meta['search_item'],
                        })
                    yield Request(
                        item['reviews_url'],
                        callback=self.parse_reviews,
                        meta=new_meta
                    )
        elif self.try_match_product_details_if_product_list_not_matches:
            # go to product details page to extract SKU and try matching again
            new_meta = safe_copy_meta(response.meta)
            new_meta['check_match'] = True
            if self.type == 'search':
                new_meta.update({
                    'search_string': response.meta['search_string'],
                    'search_item': response.meta['search_item'],
                })
            new_headers = response.headers.copy()
            new_headers['Referer'] = ''
            yield Request(
                item['url'],
                callback=self.parse_product,
                meta=new_meta,
                headers=new_headers
            )

        yield matched_any

    def _process_product_list_item_all_sellers(self, response, item):
        """
        Must yield value of matched_any as last element
        """
        matched_any = False
        if self.basic_match(response.meta, response.meta['search_item'], item):
            if self.match(response.meta, response.meta['search_item'], item):
                matched_any = True
                if self.need_details_page(item):
                    new_meta = safe_copy_meta(response.meta)
                    new_meta['check_match'] = False
                    if self.type == 'search':
                        new_meta.update({
                            'search_string': response.meta['search_string'],
                            'search_item': response.meta['search_item'],
                        })
                    new_headers = response.headers.copy()
                    new_headers['Referer'] = ''
                    yield Request(
                        item['url'],
                        callback=self.parse_product,
                        meta=new_meta,
                        headers=new_headers
                    )
                else:
                    if item.get('mbc_list_url_new') and self.collect_new_products:
                        # yield mbc parse
                        new_meta = safe_copy_meta(response.meta)
                        new_meta['found_item'] = item
                        if self.type == 'search':
                            new_meta.update({
                                'search_string': response.meta['search_string'],
                                'search_item': response.meta['search_item'],

                            })
                        new_headers = response.headers.copy()
                        new_headers['Referer'] = ''
                        yield Request(
                            item['mbc_list_url_new'],
                            callback=self.parse_mbc_list,
                            meta=new_meta,
                            headers=new_headers
                        )
                    elif item.get('mbc_list_url_used') and self.collect_used_products:
                        # yield mbc parse
                        new_meta = safe_copy_meta(response.meta)
                        new_meta.update({
                            'search_string': response.meta['search_string'],
                            'search_item': response.meta['search_item'],
                            'found_item': item
                        })
                        new_headers = response.headers.copy()
                        new_headers['Referer'] = ''
                        yield Request(
                            item['mbc_list_url_used'],
                            callback=self.parse_mbc_list,
                            meta=new_meta,
                            headers=new_headers
                        )
                    else:
                        new_meta = safe_copy_meta(response.meta)
                        new_meta['check_match'] = False
                        if self.type == 'search':
                            new_meta.update({
                                'search_string': response.meta['search_string'],
                                'search_item': response.meta['search_item'],
                            })
                        new_headers = response.headers.copy()
                        new_headers['Referer'] = ''
                        yield Request(
                            item['url'],
                            callback=self.parse_product,
                            meta=new_meta,
                            headers=new_headers
                        )
            else:
                # go to product details page to extract SKU and try matching again
                new_meta = safe_copy_meta(response.meta)
                new_meta['check_match'] = True
                if self.type == 'search':
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': response.meta['search_item'],
                    })
                new_headers = response.headers.copy()
                new_headers['Referer'] = ''
                yield Request(
                    item['url'],
                    callback=self.parse_product,
                    meta=new_meta,
                    headers=new_headers
                )
        elif self.try_match_product_details_if_product_list_not_matches:
            # go to product details page to extract SKU and try matching again
            new_meta = safe_copy_meta(response.meta)
            new_meta['check_match'] = True
            if self.type == 'search':
                new_meta.update({
                    'search_string': response.meta['search_string'],
                    'search_item': response.meta['search_item'],
                })
            new_headers = response.headers.copy()
            new_headers['Referer'] = ''
            yield Request(
                item['url'],
                callback=self.parse_product,
                meta=new_meta,
                headers=new_headers
            )
        yield matched_any

    def _process_product_info_product_details(self, response, product_info):
        """
        This needs to be in separate function because used by two methods: parse_product_details and parse_ajax_price
        """
        if response.meta.get('seller_identifier', None) and not product_info.get('seller_identifier', None):
            product_info['seller_identifier'] = response.meta['seller_identifier']

        check_match = response.meta.get('check_match', True)

        match = self.match(response.meta, response.meta['search_item'], product_info)

        if check_match and not match:
            self.log("[AMAZON] WARNING: product does not match: %s" % response.url)
            return

        if self.parse_options:
            if product_info['options'] and response.meta.get('parse_options', True):
                self.log('[AMAZON] OPTIONS FOUND => %s' % response.url)
                self.options_found = True
                self.products_with_options += 1

                for option in product_info['options']:
                    new_meta = safe_copy_meta(response.meta)
                    new_meta.update({
                        'parse_options': False,
                        'search_string': response.meta['search_string'],
                        'search_item': response.meta['search_item'],
                        'check_match': check_match
                    })
                    yield Request(
                        option['url'],
                        self.parse_product,
                        meta=new_meta,
                        dont_filter=True
                    )
                return
            else:
                if product_info['name_with_options']:
                    product_info['name'] = product_info['name_with_options']
                elif product_info['option_texts']:
                    product_info['name'] += ' [' + ', '.join(product_info['option_texts']) + ']'

        if self.type == 'asins':
            url_asin = AmazonUrlCreator.get_product_asin_from_url(product_info['url'])
            if product_info['asin'].lower() != url_asin.lower():
                self.log("[AMAZON] product ASIN '%s' does not match url ASIN '%s'. Page: %s" %
                         (product_info['asin'], url_asin, response.url))
                return

        # Amazon Direct
        if self.amazon_direct:
            product = self.construct_product(product_info, meta=response.meta)
            self.log("[AMAZON] collect parse product: %s" % product['identifier'])
            should_collect_reviews = response.meta.get('collect_reviews', True) and self.should_collect_reviews(product_info)
            if self.type == 'category' and not should_collect_reviews:
                # yield directly only if category type AND not collecting reviews
                yield product
            else:
                self._collect_amazon_direct(product, response.meta, response.meta['search_id'])
            if should_collect_reviews:
                new_meta = safe_copy_meta(response.meta)
                new_meta['found_item'] = product_info
                if self.type == 'search':
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': response.meta['search_item'],
                    })
                yield Request(
                    product_info['reviews_url'],
                    callback=self.parse_reviews,
                    meta=new_meta
                )
        # Buy Box
        elif self.only_buybox:
            if (product_info['vendor'] and self._seller_ok(product_info['vendor'])) or \
                    self.collect_products_with_no_dealer:
                product = self.construct_product(product_info, meta=response.meta)
                self.log("[AMAZON] collect parse product: %s" % product['identifier'])
                should_collect_reviews = response.meta.get('collect_reviews', True) and self.should_collect_reviews(product_info)
                if self.type == 'category' and not should_collect_reviews:
                    # yield directly only if category type AND not collecting reviews
                    yield product
                else:
                    self._collect_buybox(product, response.meta, response.meta['search_id'])
                if should_collect_reviews:
                    new_meta = safe_copy_meta(response.meta)
                    new_meta['found_item'] = product_info
                    if self.type == 'search':
                        new_meta.update({
                            'search_string': response.meta['search_string'],
                            'search_item': response.meta['search_item'],
                        })
                    yield Request(
                        product_info['reviews_url'],
                        callback=self.parse_reviews,
                        meta=new_meta
                    )
            elif not product_info['vendor']:
                # TODO: collect vendor from vendor details page
                self.log("[AMAZON] WARNING: product with no vendor: %s" % response.url)
            else:
                self.log("[AMAZON] WARNING: vendor not allowed: %s" % response.url)
        # all sellers / lowest price
        elif self.all_sellers or self.lowest_product_and_seller:
            # Go to MBC lists to get dealers prices
            collect_mbc = response.meta.get('collect_mbc', True)
            if collect_mbc and product_info.get('mbc_list_url_new') and self.collect_new_products:
                # yield mbc parse
                new_meta = safe_copy_meta(response.meta)
                new_meta['found_item'] = product_info
                if self.type == 'search':
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': response.meta['search_item'],
                    })
                yield Request(
                    product_info['mbc_list_url_new'],
                    callback=self.parse_mbc_list,
                    meta=new_meta
                )
            elif collect_mbc and product_info.get('mbc_list_url_used') and self.collect_used_products:
                # yield mbc parse
                new_meta = safe_copy_meta(response.meta)
                new_meta['found_item'] = product_info
                if self.type == 'search':
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': response.meta['search_item'],
                    })
                yield Request(
                    product_info['mbc_list_url_used'],
                    callback=self.parse_mbc_list,
                    meta=new_meta
                )
            else:
                if (product_info['vendor'] and self._seller_ok(product_info['vendor'])) or \
                        self.collect_products_with_no_dealer:
                    use_seller_id_in_identifier = False \
                        if self.lowest_product_and_seller and not self.lowest_seller_collect_dealer_identifier else True
                    product = self.construct_product(product_info, meta=response.meta,
                                                     use_seller_id_in_identifier=use_seller_id_in_identifier)
                    self.log("[AMAZON] collect parse product: %s" % product['identifier'])
                    should_collect_reviews = response.meta.get('collect_reviews', True) and self.should_collect_reviews(product_info)
                    if self.type == 'category':
                        # yield directly only if category type AND not collecting reviews
                        yield product
                    else:
                        self._collect(product, response.meta['search_id'])

                    if should_collect_reviews:
                        new_meta = safe_copy_meta(response.meta)
                        new_meta['found_item'] = product_info
                        if self.type == 'search':
                            new_meta.update({
                                'search_string': response.meta['search_string'],
                                'search_item': response.meta['search_item'],
                            })
                        yield Request(
                            product_info['reviews_url'],
                            callback=self.parse_reviews,
                            meta=new_meta
                        )
                elif not product_info['vendor']:
                    # TODO: collect vendor from vendor details page
                    if not product_info['unavailable']:
                        self.log("[AMAZON] WARNING: Could not scrape vendor from product details: %s" % response.url)
                        self.errors.append("Could not scrape vendor from product details: %s" % response.url)
                else:
                    self.log("[AMAZON] WARNING: vendor not allowed: %s" % response.url)

    def get_subrequests_for_search_results(self, response, search_results_data, max_pages=0):
        # initial subrequests
        requests = []
        if 'subrequests' not in response.meta:
            price_margins = [
                (None, 100),
                (100, 1000),
                (1000, None)
            ]
            for low_price, high_price in price_margins:
                if search_results_data.get('filter_form'):
                    filter_params = search_results_data['filter_form']['params'].copy()
                    filter_params['low-price'] = '0' if low_price is None else str(low_price)
                    if high_price is not None:
                        filter_params['high-price'] = str(high_price)
                    url = search_results_data['filter_form']['url'] + '?' + urlencode(filter_params)
                else:
                    url = AmazonUrlCreator.build_from_existing_with_price_margins(response.url, low_price, high_price)
                new_meta = safe_copy_meta(response.meta)
                new_meta['subrequests'] = {
                    'low-price': low_price,
                    'high-price': high_price,
                }
                requests.append(Request(
                    url,
                    meta=new_meta,
                    dont_filter=True,
                    callback=self.parse_product_list
                ))
        # following subrequests
        else:
            prev_req_low_price = response.meta['subrequests']['low-price']
            prev_req_low_price = 0 if prev_req_low_price is None else prev_req_low_price
            prev_req_high_price = response.meta['subrequests']['high-price']
            if prev_req_high_price and prev_req_high_price - prev_req_low_price < 2:
                self.log("[AMAZON] Can't split request. Price difference is already only 1. URL: %s" % response.url)
                requests = []
                if search_results_data.get('subcategory_urls'):
                    for url in search_results_data['subcategory_urls']:
                        new_meta = safe_copy_meta(response.meta)
                        new_meta['subrequest'] = True
                        requests.append(Request(
                            url,
                            meta=new_meta,
                            dont_filter=True,
                            callback=self.parse_product_list
                        ))
                    return requests
                else:
                    msg = 'Too many results on page: %s. Can\'t split' % response.url
                    self.errors.append(msg)
                    self.log('[AMAZON] %s' % msg)
                    return []
            products_per_page = len(search_results_data['products'])
            total_count = search_results_data['results_count']
            if products_per_page < 1:
                return []
            max_pages = int(self._max_pages if not max_pages else max_pages)
            number_of_req = (total_count / products_per_page / max_pages) + 1
            if prev_req_low_price is None:
                min_price = 0
            else:
                min_price = prev_req_low_price
            if prev_req_high_price is None:
                max_price = 10000
            else:
                max_price = prev_req_high_price
            price_diff = max_price - min_price
            price_per_req = int(round(price_diff / float(number_of_req)))
            for i in xrange(0, number_of_req):
                low_price = min_price + i * price_per_req
                high_price = low_price + price_per_req
                if low_price == 0:
                    low_price = None
                if i + 1 == number_of_req:
                    if prev_req_high_price is None:
                        high_price = None
                    else:
                        high_price = max_price

                if search_results_data.get('filter_form'):
                    filter_params = search_results_data['filter_form']['params'].copy()
                    filter_params['low-price'] = '0' if low_price is None else str(low_price)
                    if high_price is not None:
                        filter_params['high-price'] = str(high_price)
                    url = search_results_data['filter_form']['url'] + '?' + urlencode(filter_params)
                else:
                    url = AmazonUrlCreator.build_from_existing_with_price_margins(response.url, low_price, high_price)

                new_meta = safe_copy_meta(response.meta)
                new_meta['subrequests'] = {
                    'low-price': low_price,
                    'high-price': high_price
                }
                requests.append(Request(
                    url,
                    meta=new_meta,
                    dont_filter=True,
                    callback=self.parse_product_list
                ))

        return requests

    def check_number_of_results_fits(self, search_results_data, max_pages=0, response=None):
        if self.type != 'category':
            return True

        products_count = len(search_results_data['products']) if search_results_data.get('products') else 0
        total_count = search_results_data['results_count'] if search_results_data.get('results_count') else 0

        if total_count < 1:
            return True

        if not max_pages:
            max_pages = self._max_pages

        if response:
            self.log("[AMAZON] Results for page: %s" % response.url)
        self.log('[AMAZON] Number of products: %d' % products_count, level=log.DEBUG)
        self.log('[AMAZON] Total number of products: %d' % total_count, level=log.DEBUG)
        self.log('[AMAZON] Number of pages: %d' % max_pages, level=log.DEBUG)

        fits = not(products_count and max_pages * products_count < total_count)
        self.log("[AMAZON] Number of results fits: %s" % fits)

        return fits

    def parse_product_list(self, response):
        """
        This function is callback for Scrapy. It processes search results page

        TODO: incorporate cache
        """
        if self.scraper.antibot_protection_raised(response.body_as_unicode()):
            self.antibot_blocked_count += 1
            if self.should_do_retry(response):
                self.log('[AMAZON] WARNING: Amazon antibot protection detected when crawling url: %s' %
                         response.url)
                yield self.retry_download(url=response.url,
                                          metadata=response.meta,
                                          blocked=True,
                                          headers=response.headers,
                                          callback=self.parse_product_list,
                                          response=response)
                return
            else:
                self.antibot_blocked_fully_urls['parse_product_list'] += 1
                self.log('[AMAZON] WARNING: Amazon antibot protection detected, consider using proxy/tor, url: %s' %
                         response.url)
                return

        self.parsed_count['parse_product_list'] += 1

        follow_suggestions = response.meta.get("follow_suggestions", True)
        is_main_search = response.meta.get("is_main_search", True)

        data = self.scraper.scrape_search_results_page(response, amazon_direct=self.amazon_direct)

        if self.type == 'category' and data['is_non_specific_cat_results']:
            self.log("[AMAZON] WARNING: the page does not show category specific results: %s" % response.url)
            return

        # This sometimes does not work because Amazon does not show total number of products properly on the first page
        # Then when the request is split, if the total number of requests is 1 then it is just going to ignore it
        max_pages = data['max_pages'] if data.get('max_pages') else self._max_pages

        # calculate page number
        page = data.get('current_page', None)
        if not page:
            page = response.meta.get('current_page', None)
        page = int(page) if page is not None else 1

        if page == 1 and not self.check_number_of_results_fits(data, max_pages, response=response):
            requests = self.get_subrequests_for_search_results(response, data, max_pages)
            # If not splitted then it is ignored
            if len(requests) > 1:
                self.log("[AMAZON] WARNING: Number of results is too big (%d). Splitting to %d requests. URL: %s" %
                         (data['results_count'], len(requests), response.url))
                for req in requests:
                    yield req
                return

        if data['products']:
            items = data['products']
            found_for = None
            if self.type == 'search':
                found_for = response.meta['search_string']
            elif self.type == 'category':
                found_for = response.meta['category']
            self.log('[AMAZON] Found products for [%s]' % found_for)

        elif data['suggested_products'] and self.try_suggested:
            items = data['suggested_products']
            self.log('[AMAZON] No products found for [%s]. Using suggested products. URL: %s' %
                     (response.meta['search_string'], response.url))
        else:
            items = []

        if not data['products'] and follow_suggestions and self.try_suggested:
            self.log('[AMAZON] No products or suggested products found for [%s], trying suggested searches' %
                     response.meta['search_string'])
            for url in data['suggested_search_urls']:
                # yield request
                # should mark that it's referred as suggested search and as so do not check other suggestions
                new_meta = safe_copy_meta(response.meta)
                new_meta.update({
                    'search_string': response.meta['search_string'],
                    'search_item': response.meta['search_item'],
                    'follow_suggestions': False,
                    'is_main_search': False,
                })
                yield Request(
                    url,
                    meta=new_meta,
                    dont_filter=True,
                    callback=self.parse_product_list
                )

        matched_any = False

        if self.collect_products_from_list:
            # Amazon Direct
            if self.amazon_direct and not self.only_buybox and not self.all_sellers and not self.lowest_product_and_seller:
                for item in items:
                    results = list(self._process_product_list_item_amazon_direct(response, item))
                    matched_any = results[-1]
                    for req in results[:-1]:
                        yield req
            # Buy-Box
            elif self.only_buybox and not self.amazon_direct and not self.all_sellers and not self.lowest_product_and_seller:
                for item in items:
                    results = list(self._process_product_list_item_buybox(response, item))
                    matched_any = results[-1]
                    for req in results[:-1]:
                        yield req
            # All sellers / lowest price dealer
            elif self.all_sellers or self.lowest_product_and_seller:
                for item in items:
                    results = list(self._process_product_list_item_all_sellers(response, item))
                    matched_any = results[-1]
                    for req in results[:-1]:
                        yield req
        else:
            for item in items:
                new_meta = safe_copy_meta(response.meta)
                if self.type == 'search':
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': response.meta['search_item'],
                    })
                new_meta.update({
                    'check_match': True,
                })
                new_headers = response.headers.copy()
                new_headers['Referer'] = ''
                yield Request(
                    item['url'],
                    callback=self.parse_product,
                    meta=new_meta,
                    headers=new_headers
                )

        next_url = data['next_url']

        follow_next = False
        if self.type == 'category':
            follow_next = True
        elif self.type == 'search':
            # Follow to next pages only for original search
            # and suggested search if at least one product matched from first page
            # otherwise it tries to crawl the whole Amazon or something like that
            follow_next = (is_main_search or matched_any)
        if next_url and follow_next:
            if self.max_pages is None or page < self.max_pages:
                new_meta = safe_copy_meta(response.meta)
                new_meta.update({
                    'follow_suggestions': False,
                    'is_main_search': is_main_search,
                    'current_page': page + 1
                })
                yield Request(
                    next_url,
                    meta=new_meta,
                    dont_filter=True,
                    callback=self.parse_product_list
                )
            else:
                self.log('[AMAZON] Max page limit %d reached. URL: %s' % (self.max_pages, response.url))
        elif next_url:
            self.log('[AMAZON] Not following next page from %s: %s' % (response.url, next_url))
        else:
            self.log('[AMAZON] No next url from %s' % response.url)

    def parse_product(self, response):
        """
        Parse product just to get seller name
        """
        if self.scraper.antibot_protection_raised(response.body_as_unicode()):
            self.antibot_blocked_count += 1
            if self.should_do_retry(response):
                self.log('[AMAZON] WARNING: Amazon antibot protection detected when crawling url: %s' %
                         response.url)
                yield self.retry_download(url=response.url,
                                          metadata=response.meta,
                                          blocked=True,
                                          headers=response.headers,
                                          callback=self.parse_product,
                                          response=response)
            else:
                self.antibot_blocked_fully_urls['parse_product'] += 1
                self.log('[AMAZON] WARNING: Amazon antibot protection detected, consider using proxy/tor, url: %s' %
                         response.url)
            return

        self.parsed_count['parse_product'] += 1

        try:
            product_info = self.scraper.scrape_product_details_page(response, self.options_only_color,
                                                                    self.collect_new_products,
                                                                    self.collect_used_products)
        except AmazonScraperProductDetailsException:
            if self.should_do_retry(response):
                self.log('[AMAZON] WARNING: Could not parse product details page: %s' % response.url)
                yield self.retry_download(url=response.url,
                                          metadata=response.meta,
                                          callback=self.parse_product,
                                          response=response)
            else:
                self.log('[AMAZON] ERROR: Could not parse product details page: %s' % response.url)
                self.errors.append('Could not parse product details page: %s' % response.url)
            return
        if not product_info:
            self.log("[AMAZON] WARNING: no product info: %s" % response.url)
            return
        # Fix response.meta['search_string']_item and meta['search_item']. Needed for BSM spider
        if not response.meta.get('search_item'):
            response.meta['search_item'] = product_info

        # If no price found and ajax price url is present - collect price from ajax
        if not product_info['price'] and product_info['ajax_price_url']:
            new_meta = safe_copy_meta(response.meta)
            new_meta['product_info'] = product_info
            yield Request(
                product_info['ajax_price_url'],
                callback=self.parse_ajax_price,
                dont_filter=True,
                meta=new_meta
            )
            return

        for res in self._process_product_info_product_details(response, product_info):
            yield res

    def parse_reviews(self, response):
        if self.scraper.antibot_protection_raised(response.body_as_unicode()):
            self.antibot_blocked_count += 1
            if self.should_do_retry(response):
                self.log('[AMAZON] WARNING: Amazon antibot protection detected when crawling url: %s' %
                         response.url)
                yield self.retry_download(url=response.url,
                                          metadata=response.meta,
                                          blocked=True,
                                          headers=response.headers,
                                          callback=self.parse_reviews,
                                          response=response)
                return
            else:
                self.antibot_blocked_fully_urls['parse_reviews'] += 1
                self.log('[AMAZON] WARNING: Amazon antibot protection detected, consider using proxy/tor, url: %s' %
                         response.url)
                return

        self.parsed_count['parse_reviews'] += 1

        item = response.meta['found_item']
        base_identifier = get_base_identifier(item['identifier'])
        try:
            results = self.scraper.scrape_reviews_list_page(
                response, self.reviews_inc_selector, self.reviews_collect_author, self.reviews_collect_author_location)
        except IndexError:
            if self.should_do_retry(response):
                self.log('[AMAZON] WARNING: Error when scraping reviews from: %s' % response.url)
                yield self.retry_download(url=response.url,
                                          metadata=response.meta,
                                          callback=self.parse_reviews,
                                          response=response)
                return
            else:
                self.errors.append('Error when scraping reviews from: %s. Gave up retrying' % response.url)
                self.log('[AMAZON] WARNING: Error when scraping reviews from: %s. Gave up retrying' % response.url)
                return
        reviews = results['reviews']
        self.log('[AMAZON] Scraped %d reviews from %s' % (len(reviews), response.url))
        # Sort by date only if there are more urls
        too_old = False
        if results['next_url']:
            if not AmazonUrlCreator.check_review_url_is_sorted_by_date(response.url):
                url = AmazonUrlCreator.get_reviews_url_sorted_by_date(response.url)
                new_meta = safe_copy_meta(response.meta)
                yield Request(
                    url=url,
                    meta=new_meta,
                    callback=self.parse_reviews)
                return
            # Check if reviews are not too old - only if reviews for product are in prev crawl
            if self.reviews_only_new and base_identifier in self.prev_crawl_reviews:
                date_threshold = self.prev_crawl_reviews[base_identifier]
                for review in reviews:
                    if review['date'].date() < date_threshold:
                        too_old = True
                        self.log("[AMAZON] Too old review: %s. Skipping next pages" % review['date'].date())
                        break

        if results['next_url'] and not too_old:
            '''
            if results['next_url'] == '#':
                with open('amazon_reviews_next_bug_%s.html' % md5(response.body).hexdigest(), 'w') as f:
                    f.write(response.body)
            '''
            new_meta = safe_copy_meta(response.meta)
            yield Request(
                results['next_url'],
                callback=self.parse_reviews,
                meta=new_meta,
            )

        # collect reviews
        product = self.construct_product(item, meta=response.meta)

        self.log("[AMAZON] PARSING REVIEWS COMPLETE FOR: %s" % product['identifier'])

        if reviews:
            self.log("[AMAZON] Collected %d reviews" % len(reviews))
            if self.reviews_collect_author_location:
                while reviews:
                    review = reviews[0]
                    if review['author_url'] in self.review_authors:
                        review['author'] = self.review_authors[review['author_url']]
                        review['author_location'] = self.review_author_locations[review['author_url']]
                        self._collect_review(product['identifier'], review)
                        reviews = reviews[1:]
                    else:
                        other_reviews = reviews[1:]
                        new_meta = {
                            'author_url': review['author_url'],
                            'review': review,
                            'product_identifier': product['identifier'],
                            'found_item': response.meta['found_item'],
                            'other_reviews': other_reviews,
                            'collect_product': response.meta.get('collect_product', True)
                        }
                        yield Request(
                            review['author_url'],
                            callback=self.parse_review_author_location,
                            meta=new_meta,
                            dont_filter=True
                        )
                        break
            else:
                for review in reviews:
                    self._collect_review(product['identifier'], review)

    def parse_review_author_location(self, response):
        review = response.meta['review']
        product_identifier = response.meta['product_identifier']
        new_data = self.scraper.scrape_review_author_page(response)
        if not new_data:
            self.retry_download(response.url, response.meta, callback=self.parse_review_author_location,
                response=response)
            return
        self.review_authors[response.meta['author_url']] = new_data['author']
        self.review_author_locations[response.meta['author_url']] = new_data['location']
        review['author'] = new_data['author']
        review['author_location'] = new_data['location']
        self._collect_review(product_identifier, review)

        reviews = response.meta['other_reviews']
        if reviews:
            review = reviews[0]
            other_reviews = reviews[1:]
            new_meta = {
                'author_url': review['author_url'],
                'review': review,
                'product_identifier': product_identifier,
                'found_item': response.meta['found_item'],
                'other_reviews': other_reviews,
                'collect_product': response.meta.get('collect_product', True)
            }
            yield Request(
                review['author_url'],
                callback=self.parse_review_author_location,
                meta=new_meta
            )

    def _add_seller_to_cache(self, seller_id, seller_name):
        self.sellers_cache[seller_id] = seller_name

    def _get_seller_from_cache(self, seller_id):
        return self.sellers_cache.get(seller_id, None)

    def parse_mbc_list(self, response):
        if self.scraper.antibot_protection_raised(response.body_as_unicode()):
            self.antibot_blocked_count += 1
            if self.should_do_retry(response):
                self.log('[AMAZON] WARNING: Amazon antibot protection detected when crawling url: %s' %
                         response.url)
                yield self.retry_download(url=response.url,
                                          metadata=response.meta,
                                          blocked=True,
                                          headers=response.headers,
                                          callback=self.parse_mbc_list,
                                          response=response)
                return
            else:
                self.antibot_blocked_fully_urls['parse_mbc_list'] += 1
                self.log('[AMAZON] WARNING: '
                         'Amazon antibot protection detected, consider using proxy/tor, url: [{}]'.format(response.url))
                return

        self.parsed_count['parse_mbc_list'] += 1

        results = self.scraper.scrape_mbc_list_page(response)

        if not results:
            if self.should_do_retry(response):
                self.log("[[AMAZON]] Reloading MBC list: %s" % response.url)
                yield self.retry_download(url=response.url,
                                          metadata=response.meta,
                                          callback=self.parse_mbc_list,
                                          response=response)
            return

        for item in results['products']:
            if response.meta.get('found_item'):
                base_item = response.meta['found_item'].copy()
                # must retain name from product details
                # because sometimes MBC list page does not contain product name with options
                base_name = base_item.get('name', None)
                base_item.update(item)
                if base_name is not None:
                    base_item['name'] = base_name
                item = base_item
            if item['price'] is None:
                new_meta = safe_copy_meta(response.meta)
                new_meta.update({
                    '_product': item,
                    'check_match': False,
                    'collect_mbc': False,
                    'parse_options': False
                })
                if self.type == 'search':
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': response.meta['search_item'],
                    })
                yield Request(
                    item['url'],
                    callback=self.parse_product,
                    dont_filter=True,
                    meta=new_meta
                )
            elif item['vendor']:
                self._add_seller_to_cache(item['seller_identifier'], item['vendor'])
                if self._seller_ok(item['vendor']):
                    self.log('[AMAZON] COLLECTED ITEM => %s' % item['name'])
                    use_seller_id_in_identifier = False \
                            if self.lowest_product_and_seller and not self.lowest_seller_collect_dealer_identifier else True
                    product = self.construct_product(item, meta=response.meta,
                                                     use_seller_id_in_identifier=use_seller_id_in_identifier)
                    if self.type == 'category' and not self.collect_reviews:
                        yield product
                    else:
                        self._collect(product, response.meta['search_id'])
            elif self._get_seller_from_cache(item['seller_identifier']):
                seller_name = self._get_seller_from_cache(item['seller_identifier'])
                item['vendor'] = seller_name
                if self._seller_ok(item['vendor']):
                    self.log('[AMAZON] COLLECTED ITEM => %s' % item['name'])
                    use_seller_id_in_identifier = False \
                            if self.lowest_product_and_seller and not self.lowest_seller_collect_dealer_identifier else True
                    product = self.construct_product(item, meta=response.meta,
                                                     use_seller_id_in_identifier=use_seller_id_in_identifier)
                    if self.type == 'category' and not self.collect_reviews:
                        yield product
                    else:
                        self._collect(product, response.meta['search_id'])
            elif item['seller_identifier']:
                new_meta = safe_copy_meta(response.meta)
                new_meta.update({
                    '_product': item,
                    'seller_identifier': item['seller_identifier'],
                    'check_match': False,
                    'collect_mbc': False,
                    'parse_options': False
                })
                if self.type == 'search':
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': response.meta['search_item'],
                    })
                # Go and extract vendor
                # yield Request(
                #     item['url'],
                #     callback=self.parse_product,
                #     meta=new_meta
                # )
                yield Request(
                    item['seller_url'],
                    callback=self.parse_vendor,
                    dont_filter=True,
                    meta=new_meta
                )
            else:
                self.log("[AMAZON] WARNING: no seller identifier on %s" % response.url)

        # Collecting all items
        new_meta = safe_copy_meta(response.meta)
        if results['next_url']:
            yield Request(
                results['next_url'],
                callback=self.parse_mbc_list,
                meta=new_meta
            )
        elif 'found_item' in response.meta and self.should_collect_reviews(response.meta['found_item']):
            new_meta['collect_product'] = False
            yield Request(
                response.meta['found_item']['reviews_url'],
                callback=self.parse_reviews,
                meta=new_meta
            )

    def parse_vendor(self, response):
        if self.scraper.antibot_protection_raised(response.body_as_unicode()):
            self.antibot_blocked_count += 1
            if self.should_do_retry(response):
                self.log('[AMAZON] WARNING: Amazon antibot protection detected when crawling url: %s' %
                         response.url)
                yield self.retry_download(url=response.url,
                                          metadata=response.meta,
                                          blocked=True,
                                          headers=response.headers,
                                          callback=self.parse_vendor,
                                          response=response)
                return
            else:
                self.antibot_blocked_fully_urls['parse_vendor'] += 1
                self.log('[AMAZON] WARNING: '
                         'Amazon antibot protection detected, consider using proxy/tor, url: [{}]'.format(response.url))
                return

        self.parsed_count['parse_vendor'] += 1

        product_info = response.meta['_product']

        results = self.scraper.scrape_vendor_page(response)

        if not results['name']:
            if self.should_do_retry(response) and self.retry_vendor_name:
                self.log("[AMAZON] Couldn't scrape vendor name from: %s. Retrying" % response.url)
                yield self.retry_download(response.url, response.meta, self.parse_vendor,
                    response=response)
                return
            else:
                self.log("[AMAZON] Couldn't scrape vendor name from vendor page: %s. Given up" % response.url)
                # self.errors.append("Couldn't scrape vendor name from: %s. Given up" % response.url)
                new_meta = safe_copy_meta(response.meta)
                new_meta.update({
                    '_product': product_info,
                    'seller_identifier': product_info['seller_identifier'],
                    'check_match': False,
                    'collect_mbc': False,
                    'collect_reviews': False,
                    'parse_options': False
                })
                if self.type == 'search':
                    new_meta.update({
                        'search_string': response.meta['search_string'],
                        'search_item': response.meta['search_item'],
                    })
                # Go and extract vendor from product details
                yield Request(
                    product_info['url'],
                    callback=self.parse_product,
                    meta=new_meta,
                    dont_filter=True
                )
                return

        product_info['vendor'] = results['name']

        if (product_info['vendor'] and self._seller_ok(product_info['vendor'])) or \
                self.collect_products_with_no_dealer:
            product = self.construct_product(product_info, meta=response.meta)
            self.log("[AMAZON] collect parse vendor: %s" % product['identifier'])
            if self.type == 'category' and not self.collect_reviews:
                yield product
            else:
                self._collect(product, response.meta['search_id'])
        elif not product_info['vendor']:
            # TODO: collect vendor from vendor details page
            self.log("[AMAZON] WARNING: product with no vendor: %s" % response.url)
        else:
            self.log("[AMAZON] WARNING: vendor not allowed: %s" % response.url)

    def parse_ajax_price(self, response):
        self.parsed_count['parse_ajax_price'] += 1
        # TODO: add test
        price = self.scraper.scrape_price_from_ajax_price_page(response)

        product_info = response.meta['product_info']
        product_info['price'] = price

        for req in self._process_product_info_product_details(response, product_info):
            yield req

    def dummy_callback(self, response):
        """
        Dummy callback for dummy requests. Does nothing
        """


class BaseAmazonConcurrentSpiderWithCaptcha(BaseAmazonConcurrentSpider):
    use_amazon_middleware = True
    rotate_agent = False
    def retry_download(self, url, metadata, callback, blocked=False, headers=None, response=None):
        no_try = metadata.get('try', 1)
        self.log("[AMAZON] Try %d. Retrying to download %s" %
                 (no_try, url))
        if no_try < self.max_retry_count:
            captcha_url = response.xpath('//img[contains(@src, "captcha")]/@src').extract()[0]
            self.log('Getting captcha')
            try:
                captcha = get_captcha_from_url(captcha_url)
            except:
                self.log('Problems getting captcha')
                captcha = ''

            self.log('Captcha: {}'.format(captcha))
            meta = safe_copy_meta(metadata)
            meta['try'] = no_try + 1
            meta['renew_tor'] = True
            meta['recache'] = True
            meta['renew_user-agent'] = True
            meta['keep_session'] = True
            # time.sleep(self.retry_sleep)
            # Proxy Server support to exclude blocked proxy
            r = FormRequest.from_response(response, formdata={'field-keywords': captcha}, dont_filter=True,
                                          meta=meta, callback=callback,
                                          errback=lambda failure: self.retry_download(url, meta, callback))
            return r
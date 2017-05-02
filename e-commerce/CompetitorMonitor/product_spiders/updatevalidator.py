# -*- coding: utf-8 -*-

from decimal import Decimal
from cgi import escape
from utils import remove_punctuation

import config

from emailnotifier import EmailNotifier, EmailNotifierException

import requests

from error_detection.delisted_duplicates import DelistedDuplicatesDetection

def percentage_change(old_price, price):
    change = Decimal(0)

    if old_price != price:
        if not old_price:
            change = Decimal(100)
        else:
            change = Decimal(abs((price - old_price) / old_price)) * Decimal(100)

    return change


def get_matches(upload_dst, website_id):
    matches = []

    if upload_dst in config.new_system_api_roots:
        api_host = config.new_system_api_roots[upload_dst]
    else:
        return matches
    url = '%s/api/get_matched_products.json?website_id=%s&api_key=3Df7mNg' % (api_host, website_id)

    t_number = 0
    retry_query = True
    while retry_query and t_number < 10:
        t_number += 1
        try:
            r = requests.get(url, timeout=300)
            matches = r.json()['matches']
        except:
            pass
        else:
            retry_query = False

    return matches


meaning_fields = ['name', 'category', 'brand', 'dealer', 'sku', 'url']
possible_identifier_like_fields = {'sku'}
possible_identifier_containers = {'url'}


def _get_hash_without_identifier(product, config=None):
    """
    >>> product1 = {\
        'brand': 'FitFlop',\
        'category': '',\
        'dealer': '',\
        'identifier': '883945391996',\
        'image_url': 'http://demandware.edgesuite.net/sits_pod16/dw/image/v2/AAIT_PRD/on/demandware.static/Sites-FFUK-Site/Sites-fitflop/en_GB/v1420481960884/images/BonLeatherBlackboard.jpg?sw=420&sh=420&sfrm=jpg',\
        'name': 'Test',\
        'price': '54.00',\
        'shipping_cost': '',\
        'sku': '883945391996',\
        'stock': '1',\
        'url': 'http://www.fitflop.co.uk/womens/womens-sandals/bon/womens-bon-leather-blackboard/883945391996.html',\
    }
    >>> _get_hash_without_identifier(product1)
    'test::fitflop'
    >>> product2 = {\
        'identifier': 'some_id',\
        'sku': 'some_sku',\
        'name': "The Name",\
        'url': 'http://somesite.org/id=some_id',\
        'category': '',\
        'brand': '',\
        'dealer': '',\
    }
    >>> _get_hash_without_identifier(product2)
    'the name::::somesku'
    """
    def prepare_func(str):
        return remove_punctuation(str.lower())
    product_hash = ''
    if not config:
        config = _get_fields_configuration_for_hash(product)
    for field in config:
        product_hash += '%s:' % prepare_func(product[field])
    product_hash = product_hash.strip(":")
    return product_hash

def _get_fields_configuration_for_hash(product, prev_config=None):
    """
    Collects list of all fields, which can be used for hash building without identifier

    :param product: product, for which to build configuration
    :param prev_config: predefine configuration (possibly collected from previous product), will be used instead of
    full fields list; it's needed if you want to generate configuration, common to many products
    :return: list of fields, which can then be used to generate hash without identifier
    """
    if not prev_config:
        prev_config = meaning_fields
    config = []
    for field in prev_config:
        if field in possible_identifier_like_fields:
            if product[field].lower() == product['identifier'].lower():
                continue
        if field in possible_identifier_containers:
            if product['identifier'].lower() in product[field].lower():
                continue
        config.append(field)
    return config

def _get_fields_configuration_for_hash_products(products):
    """
    >>> product1 = {\
        'identifier': 'id1',\
        'name': 'product 1',\
        'category': '',\
        'brand': 'asd',\
        'dealer': '',\
        'sku': '111',\
        'url': 'http://asd.qwe/zxc',\
        'image_url': '',\
        'stock': '',\
        'shipping_cost': '',\
        'price': '',\
    }
    >>> product2 = {\
        'identifier': 'id2',\
        'name': 'product 2',\
        'category': '',\
        'brand': 'qwe',\
        'dealer': '',\
        'sku': '111',\
        'url': 'http://rr.zzz/uuu',\
        'image_url': '',\
        'stock': '',\
        'shipping_cost': '',\
        'price': '',\
    }
    >>> _get_fields_configuration_for_hash_products([product1, product2])
    ['name', 'category', 'brand', 'dealer', 'sku', 'url']
    >>> product1['sku'] = product1['identifier']
    >>> _get_fields_configuration_for_hash_products([product1, product2])
    ['name', 'category', 'brand', 'dealer', 'url']
    >>> product2['url'] = 'http://asd.zxc/?=' + product2['identifier']
    >>> _get_fields_configuration_for_hash_products([product1, product2])
    ['name', 'category', 'brand', 'dealer']
    """
    config = None
    for product in products:
        config = _get_fields_configuration_for_hash(product, prev_config=config)
    return config

'''
    MAIN CHANGES:
        1: 'The crawl contains too many additions',
        2: 'The crawl contains too many deletions',
        22: 'The crawl contains too many matched deletions',
        23: 'The crawl contains too many updates',
        3: 'The crawl contains too many changes',
        14: 'Invalid price change',
        24: 'The crawl finished with 0 items collected',
    ADDITIONAL CHANGES:
        4: 'The crawl contains too many additional changes',
        9: 'The crawl contains sku changes',
        11: 'The crawl contains too many additional changes to empty value',
        12: 'The crawl contains too many image url changes',
        13: 'The crawl contains too many category changes',
        15: 'The crawl contains too many products moved from In Stock to Out of Stock',
    IDENTIFIERS:
        10: 'The crawl contains name change for product with blank identifier',
        5: 'The crawl has products with no identifier',
        6: 'Non-unique identifier found',
        7: 'The crawl contains identifier changes',
        18: 'Product identifier has changed for product',
    INTEGRITY:
        8: 'Too long field value',
    METADATA CHANGES:
        16: 'Immutable metadata field has changed',
    REVIEWS:
        17: 'No reviews. Spider should collect reviews, but 0 reviews collected on this crawl',
    CONNECTION:
        19: 'Too many responses with error code',
        20: 'The crawler has received no response from the server',
    SPIDER ERROR ALERTS:
        21: 'Spider error alert',
'''

class UpdateValidator(object):
    check_category_changes_members = [69]

    def __init__(self):
        self._errors = []

        self.notifier = EmailNotifier(
            config.SMTP_USER, config.SMTP_PASS,
            config.SMTP_FROM, config.SMTP_HOST,
            config.SMTP_PORT)

    @property
    def errors(self):
        return self._errors

    def __send_notification_to_dev(self, spider, errors):
        receivers = []
        subject = "Found delisted duplicates for spider %s" % spider.name
        body = u"There are delisted duplicates in last crawl of spider %s:\n" % spider.name
        if errors:
            for error in errors:
                body += u'\n' + error
            try:
                body = body.encode('utf-8')
                self.notifier.send_notification(receivers, subject, body)
            except EmailNotifierException, e:
                print "Failed sending notification: %s" % e

    def get_matched_deletions(self, upload_dst, website_id, crawl_changes):
        matches = get_matches(upload_dst, website_id)
        matched_ids = [m['identifier'] for m in matches]
        deleted_products = [x for x in crawl_changes if x['change_type'] == 'deletion']
        matched_deletions_count = 0
        if matched_ids:
            for change in deleted_products:
                if change['identifier'] in matched_ids:
                    matched_deletions_count += 1

        return len(matched_ids), matched_deletions_count

    def detect_delisted_duplicates(self, current_crawl, crawl_changes):
        errors = []
        dd_detection = DelistedDuplicatesDetection(current_crawl)
        additions = [x for x in crawl_changes if x['change_type'] == 'addition']
        errors_found_count = dd_detection.detect_delisted_duplicates(additions)
        if errors_found_count:
            for error_found in dd_detection.errors:
                msg = u'Product identifier has changed for product: <i>%(name)s</i>. ' \
                      u'Old identifier: <b>%(old_identifier)s</b> (<a href="%(old_url)s" target="_blank">Old URL</a>), ' \
                      u'new identifier: <b>%(new_identifier)s</b> (<a href="%(new_url)s" target="_blank">New URL</a>).' % \
                      error_found

                errors.append((18, msg))
            dd_detection.export_delisted_duplicate_errors()

        return errors

    def valid_crawl(self,
                    current_crawl,
                    crawl_changes,
                    metadata_changes,
                    crawl_add_changes,
                    products,
                    spider_error_alerts=None,
                    immutable_metadata='',
                    reviews_mandatory=False,
                    reviews_count=0):
        if not spider_error_alerts:
            spider_error_alerts = []

        self._errors = []
        valid_crawl = True

        spider = current_crawl.spider

        # custom spider errors
        if not isinstance(spider_error_alerts, list):
            msg = escape("Spider has wrong type for 'error' attribute: %s. Must be '%s'" %
                (str(type(spider_error_alerts)), str(type(list))))
            self._errors.append((21, msg))
            valid_crawl = False
        else:
            for error in spider_error_alerts:
                valid_crawl = False
                self._errors.append((21, escape("Spider error alert: %s" % error)))

        # identifier errors
        prev_crawl_total_products = 0
        without_identifiers = 0
        non_unique_identifiers = set()
        identifiers = set()
        ignore_additional_changes = []
        if spider.ignore_additional_changes:
            ignore_additional_changes = spider.ignore_additional_changes.split('|')

        fields_max_length = [
            {'field_name': 'identifier',
             'max_length': 255,
             'errors': []},
            {'field_name': 'sku',
             'max_length': 255,
             'errors': []},
            {'field_name': 'name',
             'max_length': 1024,
             'errors': []},
            {'field_name': 'url',
             'max_length': 1024,
             'errors': []},
            {'field_name': 'brand',
             'max_length': 100,
             'errors': []},
            {'field_name': 'image_url',
             'max_length': 1024,
             'errors': []},
            {'field_name': 'category',
             'max_length': 1024,
             'errors': []},
            {'field_name': 'dealer',
             'max_length': 255,
             'errors': []},
        ]

        check_category_changes = False
        if spider.account.member_id in self.check_category_changes_members:
            check_category_changes = True

        for row in products:
            prev_crawl_total_products += 1
            identifier = row['identifier']
            if not identifier:
                without_identifiers += 1
            else:
                if identifier in identifiers:
                    non_unique_identifiers.add(identifier)
                else:
                    identifiers.add(identifier)
            for fld_to_check in fields_max_length:
                field_value = row.get(fld_to_check['field_name'])
                if isinstance(field_value, str):
                    field_value = field_value.decode('utf-8')
                if field_value and len(field_value) > fld_to_check['max_length']:
                    if field_value not in fld_to_check['errors']:
                        fld_to_check['errors'].append(field_value)

        if prev_crawl_total_products and without_identifiers and (prev_crawl_total_products != without_identifiers):
            valid_crawl = False
            self._errors.append((5, 'The crawl has products with no identifier'))
        if non_unique_identifiers:
            valid_crawl = False
            for identifier in non_unique_identifiers:
                valid_crawl = False
                self._errors.append((6, escape('Non-unique identifier found: %s' % identifier)))
        for fld_to_check in fields_max_length:
            if fld_to_check['errors']:
                valid_crawl = False
                for field_value in fld_to_check['errors']:
                    if isinstance(field_value, str):
                        field_value = field_value.decode('utf-8')
                    valid_crawl = False
                    self._errors.append((8, escape('Too long %(field_name)s, the %(field_name)s exceeds %(max_length)s characters: %(field_value)s' %
                                        {'field_name': fld_to_check['field_name'],
                                         'max_length': fld_to_check['max_length'],
                                         'field_value': field_value})))

        if len(spider.crawls) >= 2:
            prev_crawl_total_products = Decimal(spider.crawls[-2].products_count)
            total_products = Decimal(spider.crawls[-1].products_count)
            changes = Decimal(spider.crawls[-1].changes_count)
            additions = Decimal(spider.crawls[-1].additions_count)
            deletions = Decimal(spider.crawls[-1].deletions_count)
            updates = Decimal(spider.crawls[-1].updates_count)
            additional_changes = Decimal(spider.crawls[-1].additional_changes_count)

            changes_percentage_maximum = Decimal(spider.update_percentage_error or '0')
            additions_percentage_maximum = Decimal(spider.additions_percentage_error or '0')
            deletions_percentage_maximum = Decimal(spider.deletions_percentage_error or '0')
            updates_percentage_maximum = Decimal(spider.price_updates_percentage_error or '0')
            additional_changes_percentage_maximum = Decimal(spider.additional_changes_percentage_error or '0')

            # Stock changes
            stock_changes_percentage_maximum = Decimal(spider.stock_percentage_error or '0')
            stock_changes_total = 0

            # TODO: make configuration parameter
            additional_changes_to_empty_value_percentage_maximum = Decimal(spider.add_changes_empty_perc or '10')
            additional_changes_image_url_percentage_maximum = Decimal(spider.image_url_perc or '50')
            additional_changes_category_percentage_maximum = Decimal(spider.category_change_perc or '10')
            additional_changes_sku_percentage_maximum = Decimal(spider.sku_change_perc or '50')

            if total_products and prev_crawl_total_products:
                if changes_percentage_maximum and (not (changes / prev_crawl_total_products) * Decimal(100) <= changes_percentage_maximum):
                    # do not alert on too many changes, useless by themselves
                    pass
                if additions_percentage_maximum and (not ((additions / prev_crawl_total_products) * Decimal(100) <= additions_percentage_maximum)):
                    valid_crawl = False
                    self._errors.append((1, 'The crawl contains too many additions'))
                if deletions_percentage_maximum and (not ((deletions / prev_crawl_total_products) * Decimal(100) <= deletions_percentage_maximum)):
                    valid_crawl = False
                    self._errors.append((2, 'The crawl contains too many deletions'))
                if updates_percentage_maximum and (not ((updates / prev_crawl_total_products) * Decimal(100) <= updates_percentage_maximum)):
                    valid_crawl = False
                    self._errors.append((23, 'The crawl contains too many updates'))
                if spider.additional_changes_percentage_error and (not ((additional_changes / prev_crawl_total_products) * Decimal(100) <= additional_changes_percentage_maximum)):
                    # do not alert too many additional changes, useless by themselves
                    pass
            elif total_products:
                # previous crawl has no products but this crawl has some products. No error alerts
                pass
            else:
                valid_crawl = False
                self._errors.append((24, 'The crawl has finished with 0 products collected'))

            # check for delisted duplicates
            if additions and not spider.ignore_identifier_changes:
                # pick deleted products
                errors = self.detect_delisted_duplicates(current_crawl, crawl_changes)
                if errors:
                    valid_crawl = False
                    self._errors += errors

            if deletions:
                upload_dst = ''
                for dst in spider.account.upload_destinations:
                    upload_dst = dst.name
                    break
                matched_products, matched_deletions = self.get_matched_deletions(upload_dst, spider.website_id, crawl_changes)
                if matched_products and matched_deletions and (Decimal(matched_deletions) / Decimal(matched_products)) * Decimal(100) >= Decimal(5):
                    valid_crawl = False
                    self._errors.append((22, 'The crawl contains too many matched deletions'))

            additional_changes_to_empty_value_count = 0
            additional_changes_image_url_count = 0
            additional_changes_category_count = 0
            additional_changes_sku_count = 0

            # error checking for additional changes
            for change in crawl_add_changes:
                identifier = change['product_data']['identifier'] if ('identifier' in change['product_data'] and change['product_data']['identifier']) else change['product_data']['name']

                # check for identifier change
                if 'identifier' in change['changes'] and not spider.ignore_identifier_changes:
                    valid_crawl = False
                    self._errors.append((7, escape('The crawl contains identifier changes. Old: %s, new: %s' % tuple(change['changes']['identifier']))))

                # check for SKU change
                if 'sku' in change['changes'] and not (ignore_additional_changes and 'sku' in ignore_additional_changes):
                    old_value, new_value = tuple(change['changes']['sku'])
                    if old_value:
                        if hasattr(old_value, 'lower') and hasattr(new_value, 'lower'):
                            if old_value.lower() != new_value.lower():
                                additional_changes_sku_count += 1
                        elif old_value != new_value:
                            additional_changes_sku_count += 1

                # check for image url change
                if 'image_url' in change['changes']:
                    old_value, new_value = tuple(change['changes']['image_url'])
                    if old_value != new_value:
                        additional_changes_image_url_count += 1

                # check for category change
                if 'category' in change['changes']:
                    old_value, new_value = tuple(change['changes']['category'])
                    if old_value != new_value:
                        additional_changes_category_count += 1

                # Check for stock change (moved to out of stock)
                if 'stock' in change['changes']:
                    old_value, new_value = tuple(change['changes']['stock'])
                    try:
                        old_value = int(old_value)
                    except:
                        old_value = ''
                    try:
                        new_value = int(new_value)
                    except:
                        new_value = ''
                    if old_value != new_value and new_value == 0:
                        stock_changes_total += 1

                # check for name change with blank identifier
                if 'name' in change['changes'] and \
                        ('identifier' not in change['product_data'] or not change['product_data']['identifier']):
                    valid_crawl = False
                    self._errors.append((10, escape('The crawl contains name change for product with blank identifier. Old: %s, new: %s' % tuple(change['changes']['name']))))

                for field, values in change['changes'].items():
                    old_value, new_value = tuple(values)
                    if isinstance(new_value, (str, unicode)):
                        new_value = new_value.strip()
                    if old_value and not new_value and field != 'stock':
                        additional_changes_to_empty_value_count += 1

            # check if there are too many additional changes to empty value
            if prev_crawl_total_products > 0 and (additional_changes_to_empty_value_count / prev_crawl_total_products) * Decimal(100) > additional_changes_to_empty_value_percentage_maximum:
                valid_crawl = False
                self._errors.append((11, 'The crawl contains too many additional changes to empty value'))

            if prev_crawl_total_products > 0 and  (additional_changes_image_url_count / prev_crawl_total_products) * Decimal(100) > additional_changes_image_url_percentage_maximum:
                valid_crawl = False
                self._errors.append((12, 'The crawl contains too many image url changes'))

            if check_category_changes and prev_crawl_total_products > 0 and  (additional_changes_category_count / prev_crawl_total_products) * Decimal(100) > additional_changes_category_percentage_maximum:
                valid_crawl = False
                self._errors.append((13, 'The crawl contains too many category changes'))

            if prev_crawl_total_products > 0 and  (additional_changes_sku_count / prev_crawl_total_products) * Decimal(100) > additional_changes_sku_percentage_maximum:
                valid_crawl = False
                self._errors.append((9, 'The crawl contains too many SKU value changes'))

            price_changes = []
            p = Decimal(spider.max_price_change_percentage or 0)
            if spider.max_price_change_percentage:
                for change in crawl_changes:
                    # Stock change, check prices 0
                    if change['change_type'] in ('update', 'silent_update'):
                        if not change['price']:
                            stock_changes_total += 1
                    if change['change_type'] == 'update':
                        old_price = Decimal(change['old_price'] or 0)
                        if old_price:
                            current_price_change_perc = percentage_change(old_price, Decimal(change['price']))
                            if p < current_price_change_perc:
                                valid_crawl = False
                                price_changes.append((current_price_change_perc, change))
            # Order the prices by the highest difference first
            price_changes.sort(key=lambda pc: pc[0], reverse=True)
            for perc, change in price_changes:
                msg = escape('Invalid price change for %s - old price: %s, new price %s' % (change['name'], change['old_price'], change['price']))
                msg += ' <a href="%s" target="_blank">View Product</a>' % change['url']
                valid_crawl = False
                self._errors.append((14, msg))

            # Check stock changes
            if prev_crawl_total_products > 0 and (Decimal(stock_changes_total) / prev_crawl_total_products) * Decimal(100) > stock_changes_percentage_maximum:
                valid_crawl = False
                self._errors.append((15, 'The crawl contains too many products moved from In Stock to Out of Stock'))

        # Error checking for metadata changes
        if metadata_changes and immutable_metadata:
            immutable_metadata = [f.strip() for f in immutable_metadata.split(',')]
            all_fields = '*' in immutable_metadata
            for change in metadata_changes:
                updates = change.get('update') or []
                for update in updates:
                    if update['field'] in immutable_metadata or all_fields:
                        old_value = update.get('old_value', '') or ''
                        if old_value:
                            valid_crawl = False
                            product_ident = change.get('identifier') or change.get('name')
                            meta_field = update.get('field')
                            msg = escape('WARNING: immutable metadata field has changed. Product: %(ident)s | Field: %(field)s | Old: %(old_value)s, New: %(new_value)s' %
                                {'ident': product_ident, 'field': meta_field,
                                 'old_value': old_value,
                                 'new_value': update.get('value', '') or ''})
                            msg += ' <a href="%s" target="_blank">View Product</a>' % change['url']
                            valid_crawl = False
                            self._errors.append((16, msg))
                deletes = change.get('delete') or []
                for delete in deletes:
                    if delete['field'] in immutable_metadata or all_fields:
                        valid_crawl = False
                        product_ident = change.get('identifier') or change.get('name')
                        meta_field = delete.get('field')
                        msg = escape('WARNING: immutable metadata field has been deleted. Product: %(ident)s | Field: %(field)s' %
                            {'ident': product_ident, 'field': meta_field})
                        msg += ' <a href="%s" target="_blank">View Product</a>' % change['url']
                        self._errors.append((16, msg))

        if reviews_mandatory and reviews_count < 1:
            valid_crawl = False
            self._errors.append((17, "No reviews. Spider should collect reviews, but 0 reviews collected on this crawl"))

        return valid_crawl

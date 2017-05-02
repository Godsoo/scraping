# -*- coding: utf-8 -*-
__author__ = 'juraseg'
import datetime
import locale
import logging
from copy import deepcopy


def parse_review_date_locales(date_str):
    """
    Parses date trying different locales. Currently supports english, german, italian, french
    """
    locales = [
        'en_US',
        'en_GB',
        'de_DE',
        'fr_FR',
        'it_IT',
    ]

    res = None
    date_str_fixed = date_str.replace('Sept', 'Sep')
    # french date format fix like "le 27 avril 2015"
    if date_str_fixed.startswith('le '):
        date_str_fixed = date_str_fixed[3:]
    # end of french date format fix
    old_loc = locale.getlocale(locale.LC_TIME)

    for loc in locales:
        try:
            locale.setlocale(locale.LC_ALL, loc + '.utf8')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_ALL, loc)
            except locale.Error:
                logging.error("[[AMAZON SCRAPER]] Failed to set locale to: %s (with and without encoding). Skipping" % loc)

        logging.info("[[AMAZON SCRAPER]] Using locale %s" % loc)

        date_formats = (u'%B %d, %Y', u'%d %b %Y', u'%d %B %Y', u'%d. %B %Y', u'%d %b. %Y')
        for date_format in date_formats:
            try:
                res = datetime.datetime.strptime(date_str.encode("utf-8"), date_format)
            except ValueError:
                try:
                    res = datetime.datetime.strptime(date_str_fixed.encode("utf-8"), date_format)
                except ValueError:
                    res = None
                else:
                    # found suitable date format
                    break
            else:
                # found suitable date format
                break
        else:
            # date format not found - continue checking locales
            continue
        break
    else:
        # date is not parsed - log an error
        logging.error("[[AMAZON SCRAPER]] Failed to parse date: %s (%s)" % (date_str.encode('utf-8'), date_str_fixed.encode('utf-8')))

    try:
        locale.setlocale(locale.LC_ALL, old_loc)
    except locale.Error:
        pass

    return res


def get_asin_from_identifier(identifier):
    """
    >>> get_asin_from_identifier(":123:456")
    '123'
    >>> get_asin_from_identifier("123:456")
    '123'
    >>> get_asin_from_identifier("123")
    '123'
    >>> get_asin_from_identifier(":123")
    '123'
    >>> get_asin_from_identifier("123:")
    '123'
    >>> get_asin_from_identifier(":123:")
    '123'

    :param identifier: identifier in format, which is saved to CM
    :return: original amazon ASIN
    """
    parts = identifier.split(':')
    parts = [part.strip() for part in parts if part.strip()]
    return parts[0]


def safe_copy_meta(meta):
    keys_to_delete = ['try', 'retry_times', 'proxy', 'proxy_id', 'dont_filter', 'dont_retry', 'recache']
    res = deepcopy(meta)
    for key in keys_to_delete:
        if key in res:
            del(res[key])
    return res
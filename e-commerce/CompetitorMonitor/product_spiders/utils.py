# -*- coding: utf-8 -*-

import csv
import re
import sys
import json
import json.decoder
import os
import xlrd

from urlparse import urlsplit, urlunsplit
from decimal import Decimal, InvalidOperation
from urllib import quote_plus

from datetime import datetime
from datetime import date
from time import mktime

from product_spiders.config import new_system_api_roots, api_key
from product_spiders.contrib.compmon2 import Compmon2API

import unicodedata

def extract_price(s):
    price = re.search('([\d\.,]+)', s) or ''
    if price:
        price = price.groups()[0]
    price = price.replace(',', '')
    try:
        price = Decimal(price)
    except (ValueError, InvalidOperation):
        price = Decimal(0)

    return price

def extract_price_eu(s):
    """
    Extracts numeric price from string in EU format: (#.###,##)

    Uses ',' as decimal delimiter:
    >>> extract_price_eu('123,45')
    Decimal('123.45')
    >>> extract_price_eu('1.223,45')
    Decimal('1223.45')
    >>> extract_price_eu('1 223,45')
    Decimal('1223.45')
    """
    price = re.search('(\d[\d\., ]*)', s) or ''
    if price:
        price = price.groups()[0]
    price = price.replace('.', '')
    price = price.replace(' ', '')
    price = price.replace(',', '.')
    try:
        price = Decimal(price)
    except (ValueError, InvalidOperation):
        price = Decimal(0)

    return price


def get_receivers(spider, status):
    receivers = [receiver for receiver in spider.notification_receivers]

    account_receivers = [receiver for receiver in
                         spider.account.notification_receivers
                         if not receiver.spider]

    receivers += account_receivers
    receivers = set([receiver.email for receiver in receivers
                     if receiver.status == status])

    return list(receivers)


def extract_price2uk(number):
    """
    Extracts price from string.
    Formats number in UK format without commas.
    Accepts string with any characters.
    Filters them and returns number in UK format
    >>> extract_price2uk("123,45")
    Decimal('123.45')
    >>> extract_price2uk('1.233,45')
    Decimal('1233.45')
    >>> extract_price2uk('1,233.45')
    Decimal('1233.45')
    """
    if type(number) == unicode:
        number = number.encode('ascii', 'ignore')
    number = re.sub('\s+', '', number)
    m = re.search(r'[\d][\d,.]*[\d]*', number, re.UNICODE)
    if m is None:
        return Decimal(0)
    number = m.group(0)
    # check if number in UK format
    m = re.search(r'^([\d,]+\.{1}[\d]{1,2})$', number, re.UNICODE)
    if not m is None:
        number = m.group(1)
        if number is None:
            number = m.group(2)
        number = number.replace(",", "")
        try:
            return Decimal(number.replace(',', ''))
        except (ValueError, InvalidOperation):
            return Decimal(0)

    # UK format without decimal part
    m = re.search(r'^([\d,]*,[\d]{3})$', number, re.UNICODE)
    if not m is None:
        number = m.group(1)
        if number is None:
            number = m.group(2)
        number = number.replace(",", "")
        try:
            return Decimal(number.replace(',', ''))
        except (ValueError, InvalidOperation):
            return Decimal(0)

    # standard format
    m = re.search(r'^([\d\.\s]+,{1}[\d]{1,2})$', number, re.UNICODE)
    if not m is None:
        number = m.group(1)
        if number is None:
            number = m.group(2)
        number = number.replace(".", "")
        number = number.replace(",", ".")
        try:
            return Decimal(number.replace(',', ''))
        except (ValueError, InvalidOperation):
            return Decimal(0)

    # standard without decimal part
    m = re.search(r'^([\d.\s]*\.[\d]{3})$', number, re.UNICODE)
    if not m is None:
        number = m.group(1)
        if number is None:
            number = m.group(2)
        number = number.replace(".", "")
        number = number.replace(",", ".")
        try:
            return Decimal(number.replace(',', ''))
        except (ValueError, InvalidOperation):
            return Decimal(0)

    # without comma/period
    m = re.search(r'([\d\s]+)', number, re.UNICODE)
    if not m is None:
        number = m.group(0)
        number = number.replace(".", "")
        number = number.replace(",", ".")
        try:
            return Decimal(number.replace(',', ''))
        except (ValueError, InvalidOperation):
            return Decimal(0)

    return Decimal(0)


def fix_spaces(s):
    return " ".join(s.split())

u_table = dict.fromkeys(i for i in xrange(sys.maxunicode)
                    if unicodedata.category(unichr(i)).startswith('P') or
                       unicodedata.category(unichr(i)).startswith('Cc'))

import string
table = string.maketrans("", "")


def remove_punctuation(s):
    if not s:
        return ''
    elif isinstance(s, unicode):
        return s.translate(u_table)
    else:
        import string

        return s.translate(table, string.punctuation)


def remove_punctuation_and_spaces(s):
    """
    >>> remove_punctuation_and_spaces('asd qwe')
    'asdqwe'
    >>> remove_punctuation_and_spaces('asd, qwe, zxc')
    'asdqwezxc'

    """
    res = remove_punctuation(s)

    return ''.join(res.split())

if __name__ == "__main__":
    import doctest
    doctest.testmod()


def unicode_csv_dict_reader(csv_data, dialect=csv.excel, **kwargs):
    reader = csv.DictReader(csv_data, dialect=dialect, **kwargs)
    for row in reader:
        res = dict([(key, unicode(value, 'utf-8')) for key, value in row.items()])
        yield res

def url_quote(url):
    """
    >>> url_quote('asd qwe')
    'asd+qwe'
    >>> url_quote('asd+qwe')
    'asd%2Bqwe'
    >>> url_quote('asd+qwe/zxc')
    'asd%2Bqwe%2Fzxc'
    """
    res = quote_plus(url)
    return res

json_fix_regex = re.compile(r'[\s-]+([^\s^"]+[^\s^"^\\]){1}"')

def fix_json(json_str):
    """
    Function to fix json which have both single and double quotes used (by JSON standard only double are valid),
    also escapes inches

    >>> print fix_json('Small / 36"-38"')
    Small /36\\"38\\"
    """
    res = json_str[:]
    res = json_fix_regex.sub(lambda x: x.group(1) + '\\"', res)
    res = res.replace("'", '"')

    return res

class DatetimeJSONEncoder(json.JSONEncoder):
    """
    Use like this:
    json.dumps(datetime.datetime.now(), cls=DatetimeJSONEncoder)
    """

    def default(self, obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        else:
            return super(DatetimeJSONEncoder, self).default(obj)

def extract_auth_from_url(url):
    """
    >>> extract_auth_from_url("http://asd:qwe@example.com")
    ('asd', 'qwe', 'http://example.com')
    """
    s = urlsplit(url)
    new_url = urlunsplit((s.scheme, s.hostname, s.path, s.query, s.fragment))
    if s.port:
        new_url += ':%s' % s.port
    return s.username, s.password, new_url


url_regex = re.compile(
    r'^(?:http|ftp)s?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

def check_is_url(url):
    """
    >>> check_is_url("Citizen Eco-Drive Limited Edition World Time A-T Chronograph Men's Watch")
    False
    """
    if url_regex.match(url):
        return True
    else:
        return False

def write_to_json_lines_file(file_path, data, json_serialize_default=None):
    with open(file_path, 'w+') as f:
        for l in data:
            f.write(json.dumps(l, default=json_serialize_default))
            f.write('\n')

    return True

def read_json_lines_from_file(file_path):
    res = []
    with open(file_path) as f:
        for l in f:
            res.append(json.loads(l))

    return res

def read_json_lines_from_file_generator(file_path):
    with open(file_path) as f:
        for l in f:
            yield json.loads(l)

def get_crawl_meta_file(crawl_id, data_dir='data'):
    """

    :param crawl_id:
    :return: filename, file_format
    """
    filename = os.path.join(data_dir, 'meta/%s_meta.json' % crawl_id)
    if os.path.exists(filename):
        return filename, 'json'
    filename = os.path.join(data_dir, 'meta/%s_meta.json-lines' % crawl_id)
    return filename, 'json-lines'

def get_crawl_meta_changes_file(crawl_id, data_dir='data'):
    """

    :param crawl_id:
    :return: filename, file_format
    """
    filename = os.path.join(data_dir, 'meta/%s_meta_changes.json' % crawl_id)
    if os.path.exists(filename):
        return filename, 'json'
    filename = os.path.join(data_dir, 'meta/%s_meta_changes.json-lines' % crawl_id)
    return filename, 'json-lines'

def get_crawl_additional_changes_file(crawl_id, data_dir='data'):
    """

    :param crawl_id:
    :return: filename, file_format
    """
    filename = os.path.join(data_dir, 'additional/%s_changes.json' % crawl_id)
    if os.path.exists(filename):
        return filename, 'json'
    filename = os.path.join(data_dir, 'additional/%s_changes.json-lines' % crawl_id)
    return filename, 'json-lines'


'''
Crontab utils
'''

def is_weekday_today(weekday, dt=None):
    """
    Check if today is the week day, which is passed.
    0 - Monday
    1 - Tuesday
    ...
    6 - Sunday
    """
    if not dt:
        dt = datetime.now()
    return int(dt.weekday()) == int(weekday)

def _split_cron_range(cron_range):
    """
    >>> _split_cron_range("1,2")
    [1, 2]
    >>> _split_cron_range("1")
    [1]
    >>> _split_cron_range("1-4")
    [1, 2, 3, 4]
    >>> _split_cron_range("1-10,15,20")
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20]
    """
    res = []
    for part in cron_range.split(','):
        if '-' in part:
            start, end = part.split('-')
            res += range(int(start), int(end) + 1)
        else:
            res.append(int(part))
    return res

def _cron_dow_to_set(dow):
    if dow == '*':
        return set(range(0, 6 + 1))
    else:
        res = set()
        for part in _split_cron_range(dow):
            if part == 0:
                part = 6
            else:
                part -= 1
            res.add(part)
        return res

def _cron_dom_to_set(dom):
    if dom == '*':
        return set(range(0, 31 + 1))
    else:
        return set(_split_cron_range(dom))

def _cron_m_to_set(m):
    if m == '*':
        return set(range(0, 12 + 1))
    else:
        return set(_split_cron_range(m))

def is_cron_today(dom, m, dow, dt=None):
    """
    >>> date = datetime(2014, 10, 2)
    >>> is_cron_today("2", "*", "*", date)
    True
    >>> is_cron_today("2", "*", "4", date)
    True
    >>> is_cron_today("2", "*", "4,5", date)
    True
    >>> is_cron_today("2", "*", "3-5", date)
    True
    >>> is_cron_today("1-5,8", "*", "*", date)
    True
    >>> is_cron_today("2,8-15", "*", "*", date)
    True
    >>> is_cron_today("1,8-20", "*", "*", date)
    False
    >>> is_cron_today("2", "*", "3", date)
    False
    >>> is_cron_today("3", "*", "4", date)
    False
    >>> is_cron_today("*", "*", "4", date)
    True
    >>> is_cron_today("*", "2", "*", date)
    False
    >>> is_cron_today("*", "10", "*", date)
    True
    >>> is_cron_today("*", "2-9", "*", date)
    False
    >>> is_cron_today("*", "2-10", "*", date)
    True
    >>> is_cron_today("*", "9-11", "*", date)
    True
    """
    if not dt:
        dt = datetime.now()
    # transforming day-of-the-week from cron format to python format
    dow = _cron_dow_to_set(dow)
    dow_matches = dt.weekday() in dow

    dom = _cron_dom_to_set(dom)
    dom_matches = dt.day in dom

    m = _cron_m_to_set(m)
    m_matches = dt.month in m

    return dow_matches and dom_matches and m_matches

def excel_to_csv(xls_filename, csv_filename):
    wb = xlrd.open_workbook(xls_filename)
    sh = wb.sheet_by_index(0)
    csv_file = open(csv_filename, 'wb')
    wr = csv.writer(csv_file, quoting=csv.QUOTE_ALL)

    for rownum in xrange(sh.nrows):
        wr.writerow([xls_cell_value(col) for col in sh.row(rownum)])

    csv_file.close()

def xls_cell_value(col):
    if col.ctype == xlrd.XL_CELL_ERROR:
        return '#N/A'
    if col.ctype == xlrd.XL_CELL_NUMBER:
        if int(col.value) == col.value:
            return int(col.value)
    return unicode(col.value).strip().encode('utf8')

def get_cm_api_root_for_spider(spider):
    if not hasattr(spider, 'website_id'):
        raise AttributeError("Spider '%s' has no 'website_id' set" % spider.name)
    if not hasattr(spider, 'upload_dst'):
        raise AttributeError("Spider '%s' has no 'upload_dst' set" % spider.name)
    if spider.upload_dst not in new_system_api_roots:
        raise KeyError("No API root found for upload dst '%s'" % spider.upload_dst)
    api_root = new_system_api_roots[spider.upload_dst]
    return api_root


def get_matched_products_for_spider(spider):
    api_root = get_cm_api_root_for_spider(spider)

    api = Compmon2API(api_root, api_key)

    return api.get_matched_products(spider.website_id)


def gmt_datetime(gmt_time):
    return datetime.fromtimestamp(mktime(gmt_time))


def gmt_date(gmt_date):
    return date.fromtimestamp(mktime(gmt_date))

def get_file_modification_date(filename):
    t = os.path.getmtime(filename)
    return datetime.fromtimestamp(t)

def get_etc_hosts_rules():
    rules = {}
    ips = {}
    if os.path.exists('/etc/hosts'):
        with open('/etc/hosts') as f:
            for l in f:
                l = l.strip()
                if l and not l.startswith('#'):
                    ip = l.split()[0]
                    hosts = l.split()[1:]
                    if ip not in ('127.0.0.1', '127.0.1.1', '::1', 'ff02::1', 'ff02::2'):
                        for host in hosts:
                            rules[host] = ip
                            ips[ip] = host
    return rules, ips

def remove_accent_mark(s):
    """
    >>> remove_accent_mark(u'AC Milan Home Ménez No.7 Shirt 2015 2016 (Fan Style Printing)')
    u'AC Milan Home Menez No.7 Shirt 2015 2016 (Fan Style Printing)'
    """
    return ''.join((c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn'))

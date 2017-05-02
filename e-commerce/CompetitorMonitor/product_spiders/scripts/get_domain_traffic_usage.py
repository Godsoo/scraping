# -*- coding: utf-8 -*-
import csv
import json
import sys
import os
from argparse import ArgumentParser, FileType
from datetime import date, timedelta
import re

HERE = os.path.dirname(os.path.abspath(__file__))

sys.path.append(os.path.abspath(os.path.join(HERE, '..')))

sys.path.append(os.path.abspath(os.path.join(HERE, '../..')))
from product_spiders.base_spiders.localspider import LocalSpider

sys.path.append(os.path.abspath(os.path.join(HERE, '../../productspidersweb')))

from productspidersweb.models import Account, Spider, Crawl, CrawlStats
from productspidersweb.utils import get_account_dir_name, get_account_spider_classes
sys.path.append('..')

from db import Session


SPIDER_EXCEPTIONS = {
    'micheldever-micheldever.co.uk',
    'lego-usa.com',
}


def domain_is_ok(domain):
    if 'competitormonitor.com' in domain:
        return False
    return True


def get_spider_domain_from_cls(spider_cls, verbose):
    # amazon
    if hasattr(spider_cls, 'domain'):
        return spider_cls.domain
    if hasattr(spider_cls, 'lego_amazon_domain'):
        return spider_cls.lego_amazon_domain
    # usual case
    if not hasattr(spider_cls, 'allowed_domains'):
        if verbose:
            print "Spider '%s' has not allowed_domains" % spider_cls.name
        return None
    # assert hasattr(spider_cls, 'allowed_domains'), "Spider '%s' has not allowed_domains" % spider_cls.name
    for domain in spider_cls.allowed_domains:
        if domain_is_ok(domain):
            return domain
    if verbose:
        print "Couldn't find domain for spider: %s" % spider_cls.name
    return None


def cls_is_ok(spider_cls):
    if issubclass(spider_cls, LocalSpider):
        return False
    return True


def get_all_spider_domains(db_session, verbose):
    res = {}
    for account in db_session.query(Account).filter(Account.enabled == True):
        enabled_spiders = {spider.name for spider in db_session.query(Spider).filter(Spider.account_id == account.id)
            .filter(Spider.enabled == True)}
        account_dir = get_account_dir_name(account.name)
        if not account_dir:
            if verbose:
                print "Couldn't find folder for account '%s'" % account.name
            # most likely it's FMS account, or some old removed account
            continue
        spider_classes = get_account_spider_classes(account_dir)
        spider_classes = [cls for cls in spider_classes if cls.name in enabled_spiders]

        for spider_cls in spider_classes:
            if not cls_is_ok(spider_cls):
                continue
            if spider_cls.name in SPIDER_EXCEPTIONS:
                continue
            spider_domain = get_spider_domain_from_cls(spider_cls, verbose)
            if spider_domain:
                res[spider_cls.name] = spider_domain
    return res


def is_today(period):
    return period == 'today'


PERIOD_REGEX = re.compile('([\d]+)(d|w)', re.I)
modifier_multiply_mapping = {
    'd': 1,
    'w': 7
}

MONTH_PERIOD_REGEX = re.compile('([\d]+)m', re.I)


def get_months_back_date(dt, number):
    """
    >>> get_months_back_date(date(2015, 12, 11), 1)
    datetime.date(2015, 11, 11)

    :param dt:
    :param number:
    :return:
    """
    i = number
    day_num = dt.day
    prev_month_end = dt
    while i > 0:
        prev_month_end = dt.replace(day=1) - timedelta(1)
        i -= 1
    return prev_month_end.replace(day=day_num)


def get_crawl_dates_from_period(period):
    """
    >>> today_date = date.today()
    >>> get_crawl_dates_from_period('today') == [today_date]
    True
    >>> yesterday = date.today() - timedelta(days=1)
    >>> get_crawl_dates_from_period('1d') == [yesterday]
    True
    >>> expected = [yesterday - timedelta(days=1), yesterday]
    >>> get_crawl_dates_from_period('2d') == expected
    True
    >>> expected = [date.today() - timedelta(days=i) for i in xrange(7, 0, -1)]
    >>> get_crawl_dates_from_period('1w') == expected
    True
    >>> end_date = date.today()
    >>> prev_month_last_day = end_date.replace(day=1) - timedelta(days=1)
    >>> month_length = prev_month_last_day.day
    >>> expected = [end_date - timedelta(days=i) for i in xrange(month_length, 0, -1)]
    >>> get_crawl_dates_from_period('1m') == expected
    True

    :param period:
    :return:
    """
    if is_today(period):
        return [date.today()]

    m = PERIOD_REGEX.match(period)
    m2 = MONTH_PERIOD_REGEX.match(period)
    if m:
        number, modifier = m.groups()
        number = int(number)
        modifier = modifier.lower()

        days_number = number * modifier_multiply_mapping[modifier]
        return [date.today() - timedelta(days=i) for i in xrange(days_number, 0, -1)]
    elif m2:
        number = m2.groups()[0]
        number = int(number)
        start_date = get_months_back_date(date.today(), number)
        res = []
        temp_date = start_date
        while temp_date < date.today():
            res.append(temp_date)
            temp_date = temp_date + timedelta(days=1)
        return res
    else:
        assert m, "Couldn't parse %s as period" % period


def check_period(period):
    return PERIOD_REGEX.match(period) or MONTH_PERIOD_REGEX.match(period)


def get_spider_run_period(spider):
    if spider.crawl_cron is None:
        return 'daily'
    if spider.crawl_cron == '* * * * *':
        return 'daily'
    if spider.crawl_cron.startswith('* *') and spider.crawl_cron.endswith('* *') and not ',' in spider.crawl_cron:
        return 'weekly'
    else:
        return "Custom: %s" % spider.crawl_cron


def fix_domain(domain):
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain


domain_reg = re.compile(r"downloader/([^/]*)/request_bytes", re.I + re.U)


def get_spider_domain_stats_key(stats_dict, spider_domain):
    domain_key = None
    for key in stats_dict:
        m = domain_reg.search(key)
        if m:
            domain = m.group(1)
            if domain == spider_domain:
                domain_key = domain
                break
    if not domain_key:
        raise KeyError("Can't find domain data for domain %s in dict keys %s" % (spider_domain, stats_dict.keys()))

    return domain_key


def get_traffic_usage(period, verbose=False, domain_filter_fns=None):
    if domain_filter_fns is None:
        domain_filter_fns = []
    db_session = Session()
    domains = get_all_spider_domains(db_session, verbose)

    crawl_dates = get_crawl_dates_from_period(period)

    accounts = db_session.query(Account).filter(Account.enabled == True)

    accounts = {a.id: a for a in accounts}

    spiders = db_session.query(Spider)\
        .filter(Spider.enabled == True)\
        .filter(Spider.account_id.in_(accounts.keys()))

    res = {}

    for spider in spiders:
        if spider.name in SPIDER_EXCEPTIONS:
            continue
        spider_domain = domains.get(spider.name)
        if not spider_domain:
            if verbose:
                print "ERROR: couldn't find domain for spider %s" % spider.name
            continue
        spider_domain = fix_domain(spider_domain)
        filter_out = False
        for fn in domain_filter_fns:
            if not fn(spider_domain):
                filter_out = True
                break
        if filter_out:
            continue

        for crawl_date in crawl_dates:
            crawl = db_session.query(Crawl)\
                .filter(Crawl.spider_id == spider.id)\
                .filter(Crawl.status == 'upload_finished')\
                .filter(Crawl.crawl_date == crawl_date)\
                .first()

            if not crawl:
                continue

            stats = db_session.query(CrawlStats).filter(CrawlStats.crawl_id == crawl.id).first()

            if not stats:
                continue

            if spider.name not in res:
                res[spider.name] = {
                    'name': spider.name,
                    'domain': fix_domain(spider_domain),
                    'parse_method': spider.parse_method,
                    'run_period': get_spider_run_period(spider),
                    'requests': [],
                    'traffic': [],
                    'products': []
                }

            # check BSM
            stats_dict = json.loads(stats.stats_json)
            try:
                domain = get_spider_domain_stats_key(stats_dict, spider_domain)
            except KeyError:
                res[spider.name]['traffic'].append(float(stats.response_bytes))
                res[spider.name]['requests'].append(stats.request_count)
            else:
                res[spider.name]['traffic'].append(float(stats_dict['downloader/%s/response_bytes' % domain]))
                res[spider.name]['requests'].append(stats_dict['downloader/%s/request_count' % domain])
            res[spider.name]['products'].append(stats.item_scraped_count)

    for domain in res:
        res[domain]['traffic'] = sum(res[domain]['traffic']) if res[domain]['traffic'] else 0
        res[domain]['products'] = sum(res[domain]['products']) if res[domain]['products'] else 0
        res[domain]['requests'] = sum(res[domain]['requests']) if res[domain]['requests'] else 0

    return res


def print_results(res, args):
    table_format = "| {:<50} | {:<20} | {:<15} | {:<20} | {:<10} | {:<10} | {:<10} |"

    if res:
        total_traffic = sum([x['traffic'] for x in res.values()])
        total_traffic = "{:.3f} GB".format(total_traffic / 1024 / 1024 / 1024)
        total_requests = sum([x['requests'] for x in res.values()])
        total_products = sum([x['products'] for x in res.values()])

        print table_format.format("Spider", "Domain", "Parse method", "Run period", "Traffic", "Requests", "Products")
        print table_format.format("-"*50, "-"*20, "-"*15, "-"*20, "-"*10, "-"*10, "-"*10)
        for spider in sorted(res, key=lambda x: res[x]['traffic'], reverse=True):
            data = res[spider]
            traffic = data['traffic']
            if traffic < 1024 * 1024 * 1024:
                break
            if traffic > 1024 * 1024 * 1024:
                traffic = "{:.3f} GB".format(traffic / 1024 / 1024 / 1024)
            else:
                traffic = "{:.3f} MB".format(traffic / 1024 / 1024)
            products = "{:,}".format(data['products'])
            requests = "{:,}".format(data['requests'])
            print table_format.format(data['name'], data['domain'], data['parse_method'], data['run_period'], traffic, requests, products)
        print table_format.format("-"*50, "-"*20, "-"*15, "-"*20, "-"*10, "-"*10, "-"*10)
        print table_format.format('Total', '', '', '', total_traffic, total_requests, total_products)

        if args.output_file:
            writer = csv.DictWriter(args.output_file, ['name', 'domain', 'parse_method', 'run_period', 'traffic', 'requests', 'products'])
            writer.writeheader()
            for spider in sorted(res, key=lambda x: res[x]['traffic'], reverse=True):
                traffic = res[spider]['traffic']
                if traffic > 1024 * 1024 * 1024:
                    traffic = "{:.3f} GB".format(traffic / 1024 / 1024 / 1024)
                else:
                    traffic = "{:.3f} MB".format(traffic / 1024 / 1024)
                row = res[spider].copy()
                row['traffic'] = traffic
                row['products'] = "{:,}".format(row['products'])
                row['requests'] = "{:,}".format(row['requests'])
                writer.writerow(row)


if __name__ == '__main__':
    parser = ArgumentParser(description='Collects statistics of traffic usage by all spiders split by spider')
    parser.add_argument('--period', dest='period', type=str, default='1d')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--output-file', dest='output_file', type=FileType('w+'), default=None)

    args = parser.parse_args()
    if not check_period(args.period):
        print "ERROR: unknown period format: %s. Please specify format in a way: <number><d|w|m>" % args.period
        exit(1)

    res = get_traffic_usage(args.period, args.verbose)

    print_results(res, args)

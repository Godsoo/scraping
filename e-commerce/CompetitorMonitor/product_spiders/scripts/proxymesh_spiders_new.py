# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import sys
import os
import datetime
import json
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE,
                                             '../../productspidersweb')))

from productspidersweb.models import Account, Spider, Crawl, CrawlStats

sys.path.append('..')
from emailnotifier import EmailNotifier
import config

from db import Session


proxy_mapping = {
    'proxymesh': 'ProxyMesh',
    'intoproxy': 'IntoProxy',
    '91.230.243.22': 'UKProxy',
    '84.234.17.104': 'UKProxy',
    '77.68.37.101': 'UKProxy',
    '83.170.113.116': 'UKProxy',
    '78.110.170.40': 'UKProxy',
    '88.208.232.189': 'UKProxy',
    '176.227.194.130': 'UKProxy',
    '88.208.232.57': 'UKProxy',
    '81.94.203.74': 'UKProxy',
    '77.68.68.30': 'UKProxy',
    '83.170.117.26': 'UKProxy',
}

usage_limits = {
    'ProxyMesh': 100 * 1024 * 1024 * 1024,
    # 'IntoProxy': 10 * 1024 * 1024 * 1024,
    'UKProxy': 10 * 1024 * 1024 * 1024,
}

emails = [
    'yuri.abzyanov@intelligenteye.com',
    'james.mishreki@intelligenteye.com',
    'toni.fleck@intelligenteye.com',
    'emiliano.rudenick@intelligenteye.com',
    'steven.seaward@intelligenteye.com'
]


def report(db_session, days_back):
    start_date = (datetime.datetime.now() - datetime.timedelta(days=days_back)).date()
    end_date = datetime.date.today()

    accounts = db_session.query(Account).all()
    accounts = {x.id: x for x in accounts}

    spiders = db_session.query(Spider).all()
    for spider in spiders:
        spider.account_name = accounts[spider.account_id].name if spider.account_id in accounts else ''
    spiders = {x.id: x for x in spiders}

    proxies_report = defaultdict(int)
    spiders_report = defaultdict(lambda: defaultdict(int))

    crawl_stats = db_session.query(CrawlStats.stats_json, Crawl.spider_id).join(Crawl, CrawlStats.crawl_id == Crawl.id) \
        .filter(Crawl.crawl_date >= start_date).filter(Crawl.crawl_date < end_date)

    for stats_json, spider_id in crawl_stats:
        stats = json.loads(stats_json)

        if 'proxies' not in stats:
            continue
        proxy = stats['proxies']
        proxy_name = None
        for host, name in proxy_mapping.items():
            if host in proxy:
                proxy_name = name
                break
        if proxy_name is None:
            continue
        spider = spiders[spider_id]

        traffic = stats['downloader/response_bytes']

        proxies_report[proxy_name] += traffic

        spiders_report[spider][proxy_name] += traffic

    if len(proxies_report) > 0:
        send_report(proxies_report, spiders_report, days_back)


def send_report(proxies_report, spiders_report, days_back):
    notifier = EmailNotifier(config.SMTP_USER, config.SMTP_PASS,
                             config.SMTP_FROM, config.SMTP_HOST,
                             config.SMTP_PORT)

    header = 'Report on proxy usage for last %d days' % days_back

    body = "Hello\n\nThis is automatic report of proxy traffic usage, generated for last %d days.\n" % days_back

    for proxy_name, traffic in proxies_report.items():
        body += "\n\n"
        body += "%s:\n\n" % proxy_name
        if proxy_name in usage_limits:
            if traffic > usage_limits[proxy_name]:
                body += "WARNING!!! Usage is too high: %0.4f GB (max allowed: %0.1f GB)\n" % \
                        ((float(traffic) / 1024 / 1024 / 1024), (float(usage_limits[proxy_name]) / 1024 / 1024 / 1024))
            else:
                body += "Usage is OK: %0.4f GB (max allowed: %0.1f GB)\n" % \
                        ((float(traffic) / 1024 / 1024 / 1024), (float(usage_limits[proxy_name]) / 1024 / 1024 / 1024))
        else:
            body += "Overall usage: %0.4f GB\n" % (float(traffic) / 1024 / 1024 / 1024)

        users = [(x, y[proxy_name]) for x, y in spiders_report.items() if proxy_name in y]

        if users:
            body += "\n"
            body += "Most offensive spiders:\n"
            for spider, spider_traffic in sorted(users, key=lambda x: x[1], reverse=True)[:10]:
                body += "%s (%s): %0.4f GB\n" % (spider.name, spider.account_name, float(spider_traffic) / 1024 / 1024 / 1024)

    body += "\n\n"
    body += "Best regards"

    notifier.send_notification(emails,
                               header,
                               body)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        days_back = int(sys.argv[1])
    else:
        days_back = 14
    db_session = Session()
    report(db_session, days_back)
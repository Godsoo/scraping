# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import sys
import os
import datetime
import csv

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE,
                                             '../../productspidersweb')))

from productspidersweb.models import Account, Spider, Crawl, ProxyList
sys.path.append('..')

from db import Session

if __name__ == '__main__':
    if len(sys.argv) > 1:
        days_back = int(sys.argv[1])
    else:
        days_back = 14
    db_session = Session()

    proxies = db_session.query(ProxyList).filter(ProxyList.proxies.like('%proxymesh.com%')).all()

    spiders = db_session.query(Spider)\
        .filter(Spider.enabled == True)\
        .filter(Spider.proxy_list_id.in_([x.id for x in proxies]))\
        .all()

    period_start = datetime.date.today() - datetime.timedelta(days=days_back)
    period_end = datetime.date.today()

    data = []

    for spider in spiders:
        crawls = db_session.query(Crawl)\
            .filter(Crawl.spider_id == spider.id)\
            .filter(Crawl.crawl_date > period_start)\
            .filter(Crawl.crawl_date <= period_end)\
            .filter(Crawl.status.in_(['crawl_finished', 'errors_found', 'processing_finished',
                                      'upload_finished', 'upload_errors']))

        if crawls.count() < 1:
            continue

        products_count_all = sum([x.products_count for x in crawls])
        if products_count_all < 1:
            continue
        products_count = max([x.products_count for x in crawls])

        if products_count < 1000:
            continue

        account = db_session.query(Account).get(spider.account_id)

        data.append({
            'id': spider.id,
            'name': spider.name,
            'account_id': account.id,
            'account_name': account.name,
            'parse_method': spider.parse_method,
            'crawl_method': spider.crawl_method2.crawl_method if spider.crawl_method2 else None,
            'products_count_all': products_count_all,
            'products_count': products_count
        })

    if data:
        data = sorted(data, key=lambda x: x['products_count'], reverse=True)
        keys = ['id', 'name', 'account_id', 'account_name', 'parse_method', 'crawl_method', 'products_count_all',
                'products_count']
        writer = csv.DictWriter(open('proxymesh_report.csv', 'w+'), keys)
        writer.writeheader()
        writer.writerows(data)
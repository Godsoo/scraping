# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import sys
import os
import csv

from sqlalchemy import desc

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE,
                                             '../../productspidersweb')))

from productspidersweb.models import Account, Spider, Crawl
sys.path.append('..')

from db import Session

if __name__ == '__main__':
    db_session = Session()

    amazon_spiders = db_session.query(Spider)\
        .filter(Spider.enabled == True)\
        .filter(Spider.name.like('%amazon%'))

    data = []

    for spider in amazon_spiders:
        crawl = db_session.query(Crawl)\
            .filter(Crawl.spider_id == spider.id)\
            .filter(Crawl.status.in_(['crawl_finished', 'processing_finished', 'upload_finished', 'upload_errors']))\
            .order_by(desc(Crawl.crawl_date))\
            .first()

        if not crawl:
            continue

        account = db_session.query(Account).get(spider.account_id)

        data.append({
            'id': spider.id,
            'name': spider.name,
            'account_id': account.id,
            'account_name': account.name,
            'last_crawl_id': crawl.id
        })

    if data:
        keys = ['id', 'name', 'account_id', 'account_name', 'last_crawl_id']
        writer = csv.DictWriter(open('amazon_spiders.csv', 'w+'), keys)
        writer.writeheader()
        writer.writerows(data)
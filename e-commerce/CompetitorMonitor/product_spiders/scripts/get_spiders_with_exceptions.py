# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import sys
import os
import json
import csv

from sqlalchemy import desc

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE,
                                             '../../productspidersweb')))

sys.path.append('..')

from productspidersweb.models import Account, Spider, Crawl, CrawlStats

from db import Session


def get_spiders_with_exceptions(db_session):
    results = {}

    accounts = {a.id: a.name for a in db_session.query(Account)}

    spiders = db_session.query(Spider)\
        .filter(Spider.enabled == True)\
        .join(Account, Account.id == Spider.account_id)\
        .filter(Account.enabled == True)

    for spider in spiders:
        latest_crawl = db_session.query(Crawl)\
            .filter(Crawl.spider_id == spider.id)\
            .filter(Crawl.status == 'upload_finished')\
            .order_by(desc(Crawl.crawl_date))\
            .first()
        if not latest_crawl:
            continue
        stats = db_session.query(CrawlStats).filter(CrawlStats.crawl_id == latest_crawl.id).first()
        if not stats:
            print "No stats for crawl %s of spider %s" % (latest_crawl.id, spider.id)
            continue

        stats = json.loads(stats.stats_json)

        exceptions = {}

        for k, v in stats.items():
            if 'spider_exceptions' in k:
                exceptions[k] = v

        if exceptions:
            results[spider.name] = {
                'exceptions': exceptions,
                'exceptions_count': sum([v for v in exceptions.values()]),
                'account_name': accounts[spider.account_id],
                'priority': spider.priority_possible_errors,
            }

    return results

if __name__ == '__main__':
    db_session = Session()

    if len(sys.argv) < 2:
        print "Usage: %s <results_filename>" % sys.argv[0]
        exit(1)

    output_filename = sys.argv[1]

    results = get_spiders_with_exceptions(db_session)

    if not results:
        print "No spiders with exceptions"
    else:
        with open(output_filename, 'w+') as f:
            writer = csv.DictWriter(f, ['priority', 'account', 'spider', 'number of exceptions'])
            writer.writeheader()

            def sorting_fn(data):
                spider_name, data = data
                return -data['priority'], -data['exceptions_count']

            for spider_name, data in sorted(results.items(), key=sorting_fn):
                writer.writerow({
                    'priority': "Yes" if data['priority'] else "No",
                    'account': data['account_name'],
                    'spider': spider_name,
                    'number of exceptions': data['exceptions_count']
                })

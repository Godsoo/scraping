#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import json
import datetime
from collections import defaultdict

import psycopg2
import psycopg2.extras


conn = psycopg2.connect("dbname=productspiders user=productspiders")
c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# threshold is 100 GB per week
threshold = 100 * 1024 * 1024 * 1024

proxymesh_mapping = 'proxymesh'

def to_gbs(bytes):
    return float(bytes) / 1024 / 1024 / 1024


def get_proxy_mesh_usage(days=7):
    start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).date()
    end_date = datetime.date.today()

    c.execute("select * from account")
    accounts = c.fetchall()
    accounts = {x['id']: x for x in accounts}

    c.execute("select * from spider")
    spiders = c.fetchall()
    for spider in spiders:
        spider['account_name'] = accounts[spider['account_id']]['name'] if spider['account_id'] in accounts else ''
    spiders = {x['id']: x for x in spiders}

    proxymesh_traffic = 0
    spiders_report = defaultdict(int)

    c.execute("select cs.stats_json, c.spider_id from crawl_stats cs join crawl c on c.id=cs.crawl_id "
              "where c.crawl_date >= %s and c.crawl_date < %s", (start_date, end_date))

    crawl_stats = c.fetchall()

    for row in crawl_stats:
        stats_json = row['stats_json']
        spider_id = row['spider_id']
        stats = json.loads(stats_json)

        if 'proxies' not in stats:
            continue
        proxy = stats['proxies']
        if proxymesh_mapping not in proxy:
            continue
        spider = spiders[spider_id]

        traffic = stats['downloader/response_bytes']

        proxymesh_traffic += traffic

        spiders_report[spider['name']] += traffic

    return proxymesh_traffic, spiders_report


if __name__ == '__main__':
    traffic, spiders = get_proxy_mesh_usage(days=7)

    if traffic > threshold:
        if len(sys.argv) > 1 and sys.argv[1] == 'verbose':
            print "f"
            print "Usage: %0.3f GB" % to_gbs(traffic)
            print ""
            print "Spiders sorted by most usage:"
            for spider, spider_traffic in sorted(spiders.items(), key=lambda x: x[1], reverse=True):
                if to_gbs(spider_traffic) < 0.001:
                    break
                print "%0.3f GB: %s" % (to_gbs(spider_traffic), spider)
        else:
            print 'f'
    else:
        print 't'
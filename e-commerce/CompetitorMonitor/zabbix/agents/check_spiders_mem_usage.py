#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'juraseg'
import sys
import os.path
import datetime

import psycopg2
import psycopg2.extras

here = os.path.abspath(os.path.dirname(__file__))

conn = psycopg2.connect("dbname=productspiders user=productspiders")
c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def check_spiders_mem_usage():
    # check for resource usage in last hour
    period_start = datetime.datetime.now() - datetime.timedelta(seconds=3600)
    # check for resource usage where mem usage is no less than 15%
    percentage_threshold = 15
    c.execute("SELECT * FROM spider_resources_usage "
              "WHERE time >= '%s' and mem_usage >= %s;" %
              (period_start, percentage_threshold))
    spiders = {x['spider_id']: x for x in c}
    res_ids = []
    for s_id in spiders:
        # check spider is still active
        c.execute("SELECT * FROM crawl "
                  "WHERE spider_id=%s and status='running'" % s_id)
        if len(c.fetchone()) > 0:
            res_ids.append(str(s_id))

    if res_ids:
        c.execute("SELECT * FROM spider where id in (%s)" % ",".join(res_ids))
        return [x['name'] for x in c]
    else:
        return []


if __name__ == '__main__':
    errors_spiders = check_spiders_mem_usage()
    verbose = False
    if len(sys.argv) > 1 and sys.argv[1] == 'verbose':
        verbose = True
    if not errors_spiders:
        if not verbose:
            print 't'
    else:
        if verbose:
            for spider in errors_spiders:
                print spider
        else:
            print 'f'

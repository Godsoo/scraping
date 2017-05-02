#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import psycopg2
import psycopg2.extras
import json
from datetime import datetime, timedelta, date
import os

here = os.path.abspath(os.path.dirname(__file__))

conn = psycopg2.connect("host=localhost dbname=productspiders user=productspiders")
c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


TIMEOUT_SECONDS = 18 * 60 * 60  # 18 hours in minutes

DATETIME_FORMAT = '%c'


class DatetimeJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime(DATETIME_FORMAT)
        else:
            return super(DatetimeJSONEncoder, self).default(obj)


def datetime_parser(dct):
    for k, v in dct.items():
        if isinstance(v, basestring):
            try:
                dct[k] = datetime.strptime(v, DATETIME_FORMAT)
            except ValueError:
                pass
    return dct


def check_too_long_scheduled_spiders():
    spider_stats = {}
    fname = os.path.join(here, 'spider_scheduled_time.json')
    if os.path.exists(fname) and not os.stat(fname).st_size == 0:
        try:
            spider_stats = json.load(open(fname), object_hook=datetime_parser)
        except (ValueError, AttributeError, TypeError, KeyError):
            return True, ['JSON loading error']
    c.execute("SELECT s.* FROM spider s JOIN account a ON a.id=s.account_id WHERE a.enabled AND s.enabled;")
    spiders = {x['id']: x for x in c}
    spider_ids = spiders.keys()

    c.execute("select * from crawl where spider_id in %s and status='scheduled'" % (
    tuple(spider_ids), ))

    errors = False
    errors_spiders = []
    scheduled = []
    crawls = c.fetchall()

    for crawl in crawls:
        spider = spiders[crawl['spider_id']]
        s_stats = spider_stats.get(spider['name'])
        c.execute('select * from crawl where id = %s' % crawl['id'])
        crawl = c.fetchone()
        crawl_date = crawl['crawl_date']
        if crawl['status'] == 'scheduled':
            scheduled.append(spider['name'])
            if s_stats and s_stats + timedelta(seconds=TIMEOUT_SECONDS) < datetime.now():
                errors = True
                errors_spiders.append(spider['name'])
            elif not s_stats:
                if crawl_date < date.today():
                    spider_stats[spider['name']] = datetime(crawl_date.year, crawl_date.month, crawl_date.day) + \
                                                   timedelta(days=1)
                else:
                    spider_stats[spider['name']] = datetime.now()
        elif s_stats:
            del spider_stats[spider['name']]

    for k in spider_stats.keys():
        if k not in scheduled:
            del spider_stats[k]

    with open(fname, 'w+') as f:
        json.dump(spider_stats, f, cls=DatetimeJSONEncoder)

    return errors, errors_spiders


if __name__ == '__main__':
    errors, errors_spiders = check_too_long_scheduled_spiders()
    task = 'status'
    if len(sys.argv) > 1:
        task = sys.argv[1]

    if task == 'status':
        if errors:
            print 'f'
        else:
            print 't'
    elif task == 'list':
        for spider in errors_spiders:
            print spider
    else:
        print "Unknown command: '%s'" % task

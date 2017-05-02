#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import psycopg2
import psycopg2.extras
import requests
import requests.exceptions
import pickle
from datetime import datetime, timedelta
import os

here = os.path.abspath(os.path.dirname(__file__))

conn = psycopg2.connect("dbname=productspiders user=productspiders")
c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def get_log_url(c, spider, crawl):
    server = None
    if crawl['worker_server_id']:
        c.execute("select * from worker_server where id = %s" % crawl['worker_server_id'])
        server = c.fetchone()

    if not server:
        if spider['enable_multicrawling']:
            scrapy_url = 'http://localhost:6801/'
        else:
            scrapy_url = 'http://localhost:6800/'
    else:
        scrapy_url = server['scrapy_url']

    log_url = scrapy_url + 'logs/default/%s/%s.log' % (spider['name'], crawl['jobid'])
    return log_url


def check_log_exists(log_url):
    try:
        r = requests.get(log_url)
    except requests.exceptions.RequestException as e:
        return False

    if r.status_code == 200:
        return True
    elif r.status_code == 404:
        return False
    else:
        print "Wrong status code when checking log file %s: %s" % (str(r.status_code), log_url)


def check_failed_scheduled_spiders():
    spider_stats = {}
    fname = os.path.join(here, 'spider_stats.p')
    if os.path.exists(fname) and not os.stat(fname).st_size == 0:
        spider_stats = pickle.load(open(fname))
    c.execute("SELECT s.* FROM spider s JOIN account a ON a.id=s.account_id WHERE a.enabled AND s.enabled;")
    spiders = {x['id']: x for x in c}
    spider_ids = spiders.keys()

    c.execute("select * from crawl where spider_id in %s and status='scheduled' and jobid is not null" % (
    tuple(spider_ids), ))

    errors = False
    errors_spiders = []
    scheduled = []
    crawls = c.fetchall()

    for crawl in crawls:
        if 'jobid' not in crawl:
            continue
        jobid = crawl['jobid']
        spider = spiders[crawl['spider_id']]

        log_url = get_log_url(c, spider, crawl)
        s_stats = spider_stats.get(spider['name'])

        if check_log_exists(log_url):
            c.execute('select * from crawl where id = %s' % crawl['id'])
            crawl = c.fetchone()
            if crawl['status'] == 'scheduled':
                scheduled.append(spider['name'])
                if s_stats and s_stats + timedelta(minutes=30) < datetime.now():
                    errors = True
                    errors_spiders.append(spider['name'])
                elif not s_stats:
                    spider_stats[spider['name']] = datetime.now()
            elif s_stats:
                del spider_stats[spider['name']]

    for k in spider_stats.keys():
        if k not in scheduled:
            del spider_stats[k]

    f = open(fname, 'w')
    pickle.dump(spider_stats, f)
    f.close()

    return errors, errors_spiders


if __name__ == '__main__':
    errors, errors_spiders = check_failed_scheduled_spiders()
    for spider in errors_spiders:
        if 'eglobal' in spider:
            print 'restarting', spider
            c.execute('select c.id from crawl c inner join spider s on c.spider_id=s.id where s.name=%s', (spider,))
            crawl = c.fetchone()

            c.execute('delete from deletions_review where crawl_id=%s', (crawl['id'],))
            c.execute('delete from crawl_stats where crawl_id=%s', (crawl['id'],))
            c.execute('delete from crawl where id=%s', (crawl['id'],))
            conn.commit()

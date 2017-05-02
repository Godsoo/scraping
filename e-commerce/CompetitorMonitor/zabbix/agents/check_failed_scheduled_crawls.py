#!/usr/bin/python
# -*- coding: utf-8 -*-
import cPickle as pickle
import os
import sys
from datetime import datetime, timedelta

import requests
import requests.exceptions
from psql_conn import c

here = os.path.abspath(os.path.dirname(__file__))


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


error_timeout = 30  # 30 minutes


def check_failed_scheduled_spiders():
    spider_stats = {}
    fname = os.path.join(here, 'spider_stats.p')
    if os.path.exists(fname) and not os.stat(fname).st_size == 0:
        try:
            spider_stats = pickle.load(open(fname))
        except (pickle.UnpicklingError, AttributeError, TypeError, ValueError, KeyError):
            return True, ['Unpickling error']
    c.execute("SELECT s.* FROM spider s JOIN account a ON a.id=s.account_id WHERE a.enabled AND s.enabled;")
    spiders = {x['id']: x for x in c}
    spider_ids = spiders.keys()

    c.execute("select * from crawl where spider_id in %s and status in ('scheduled_on_worker', 'scheduled')" % (
    tuple(spider_ids), ))

    errors = False
    errors_spiders = []
    # all spiders with "scheduled" or "scheduled_on_worker" status
    scheduled = []
    crawls = c.fetchall()

    for crawl in crawls:
        spider = spiders[crawl['spider_id']]

        jobid = crawl['jobid']

        log_url = get_log_url(c, spider, crawl)
        s_stats = spider_stats.get(spider['name'])

        # check if log exists
        # if status is 'scheduled' or 'scheduled_on_worker' and there is log file then it's an error
        log_exists = check_log_exists(log_url)
        # if status is 'scheduled_on_worker' and jobid is not set then it's an error
        jobid_not_set = (crawl['status'] == 'scheduled_on_worker' and not bool(jobid))

        if log_exists or jobid_not_set:
            c.execute('select * from crawl where id = %s' % crawl['id'])
            crawl = c.fetchone()
            if crawl['status'] == 'scheduled_on_worker' or crawl['status'] == 'scheduled':
                scheduled.append(spider['name'])
                if s_stats and s_stats + timedelta(minutes=error_timeout) < datetime.now():
                    errors = True
                    errors_spiders.append(spider['name'])
                elif not s_stats:
                    spider_stats[spider['name']] = datetime.now()
            elif s_stats:
                del spider_stats[spider['name']]

    for k in spider_stats.keys():
        if k not in scheduled:
            del spider_stats[k]

    with open(fname, 'w') as f:
        pickle.dump(spider_stats, f)

    return errors, errors_spiders


from check_failed_scheduled_crawls_new import check_failed_scheduled_spiders as check_failed_scheduled_spiders_new


if __name__ == '__main__':
    errors, errors_spiders = check_failed_scheduled_spiders()
    errors2, errors_spiders2 = check_failed_scheduled_spiders_new()
    errors = errors or errors2
    errors_spiders = list(set(errors_spiders + errors_spiders2))

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

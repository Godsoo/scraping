#!/usr/bin/python
# -*- coding: utf-8 -*-
import os.path
import cPickle as pickle
from datetime import datetime, timedelta

import requests

from psql_conn import c

here = os.path.abspath(os.path.dirname(__file__))

global_jobs_list = {}


def get_jobs_list_url(c, spider, crawl):
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

    jobs_url = scrapy_url + 'listjobs.json?project=default'
    return jobs_url


def get_jobs_list(c, spider, crawl):
    jobs_list_url = get_jobs_list_url(c, spider, crawl)

    if jobs_list_url in global_jobs_list:
        return global_jobs_list[jobs_list_url]
    try:
        r = requests.get(jobs_list_url)
    except requests.exceptions.RequestException as e:
        return None

    if r.status_code == 200:
        return r.json()
    else:
        return None


status_map = {
    'running': 'running',
    'scheduled_on_worker': 'pending'
}


def check_job_has_status_on_remote(c, spider, crawl, status):
    jobs_list = get_jobs_list(c, spider, crawl)

    if not jobs_list:
        return False

    jobid = crawl['jobid']

    scrapy_status = status_map[status]

    for job in jobs_list.get(scrapy_status, []):
        if job['id'] == jobid:
            return True
    return False


def check_job_has_status(c, spider, crawl, status):
    server = None
    if crawl['worker_server_id']:
        c.execute("select * from worker_server where id = %s" % crawl['worker_server_id'])
        server = c.fetchone()

    if not server:
        return False
    return check_job_has_status_on_remote(c, spider, crawl, status)


error_timeout = 30  # 30 minutes


def check_failed_spiders_with_status(status):
    spider_stats = {}
    fname = os.path.join(here, 'spider_stats_%s_new.p' % status)
    if os.path.exists(fname) and not os.stat(fname).st_size == 0:
        try:
            spider_stats = pickle.load(open(fname))
        except (pickle.UnpicklingError, AttributeError, TypeError, ValueError, KeyError):
            return True, ['Unpickling error']

    c.execute("select s.* from spider s join account a on a.id=s.account_id where a.enabled and s.enabled;")
    spiders = {x['id']: x for x in c}
    spider_ids = spiders.keys()

    c.execute("select * from crawl where spider_id in %s and status='%s'" % (tuple(spider_ids), status))

    errors = False
    errors_spiders = []
    spiders_with_status = []
    crawls = c.fetchall()

    for crawl in crawls:
        if 'jobid' not in crawl:
            continue
        spider = spiders[crawl['spider_id']]

        s_stats = spider_stats.get(spider['name'])

        if not check_job_has_status(c, spider, crawl, status):
            c.execute('select * from crawl where id = %s' % crawl['id'])
            crawl = c.fetchone()
            if crawl['status'] == status:
                spiders_with_status.append(spider['name'])
                if s_stats and s_stats + timedelta(minutes=error_timeout) < datetime.now():
                    errors = True
                    errors_spiders.append(spider['name'])
                elif not s_stats:
                    spider_stats[spider['name']] = datetime.now()
            elif s_stats:
                del spider_stats[spider['name']]

    for k in spider_stats.keys():
        if k not in spiders_with_status:
            del spider_stats[k]

    with open(fname, 'w') as f:
        pickle.dump(spider_stats, f)

    return errors, errors_spiders


def check_failed_scheduled_spiders():
    return check_failed_spiders_with_status('scheduled_on_worker')

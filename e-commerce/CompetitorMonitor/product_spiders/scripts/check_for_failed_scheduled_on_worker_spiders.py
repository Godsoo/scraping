# -*- coding: utf-8 -*-
import warnings
warnings.simplefilter("ignore")

import sys
import os
import time
from datetime import datetime, timedelta
import requests
import dateutil.parser


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE, '..')))
sys.path.append(os.path.abspath(os.path.join(HERE, '../..')))
sys.path.append(os.path.abspath(os.path.join(HERE, '../../productspidersweb')))
from productspidersweb.models import Account, Spider, Crawl, WorkerServer
sys.path.append('..')

from product_spiders.export import export_errors
from product_spiders.config import DATA_DIR
from product_spiders.spiderretrymanager import SpiderRetryManager

from db import Session


status_map = {
    'running': 'running',
    'scheduled_on_worker': 'pending'
}

error_not_on_worker_timeout = 120
error_started_timeout = 120


global_jobs_list = {}


def get_jobs_list_url(db_session, spider, crawl):
    server = db_session.query(WorkerServer).filter(WorkerServer.id == crawl.worker_server_id).first()
    scrapy_url = server.scrapy_url

    jobs_url = scrapy_url + 'listjobs.json?project=default'
    return jobs_url


def get_jobs_list(jobs_list_url):
    print time.ctime(), jobs_list_url
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


def get_jobs_list_db(db_session, spider, crawl):
    jobs_list_url = get_jobs_list_url(db_session, spider, crawl)

    return get_jobs_list(jobs_list_url)


def check_crawl_has_status_on_worker(db_session, spider, crawl, status):
    jobs_list = get_jobs_list_db(db_session, spider, crawl)
    status_on_worker = status_map[status]
    pending_list = jobs_list[status_on_worker]

    for job in pending_list:
        if job['id'] == crawl.jobid:
            return True
    return False


def get_crawl_status_on_worker(db_session, spider, crawl):
    jobs_list = get_jobs_list_db(db_session, spider, crawl)

    for status in jobs_list:
        # skip non-status keys
        if not isinstance(jobs_list[status], list):
            continue
        for job in jobs_list[status]:
            if job['id'] == crawl.jobid:
                if job.get('start_time'):
                    job['start_time'] = dateutil.parser.parse(job['start_time'])
                if job.get('end_time'):
                    job['end_time'] = dateutil.parser.parse(job['end_time'])
                return status, job
    return None, None


def _get_active_spiders_map(db_session):
    spiders = db_session.query(Spider).join(Account).filter(Account.enabled == True).filter(Spider.enabled == True)
    spiders = {s.id: s for s in spiders}
    return spiders


def get_failed_crawls_scheduled_on_worker(db_session, crawls):
    error_crawl_ids = []

    for crawl in crawls:
        if not crawl.jobid:
            continue
        spider = db_session.query(Spider).get(crawl.spider_id)

        status, job = get_crawl_status_on_worker(db_session, spider, crawl)

        if not status:
            if crawl.scheduled_on_worker_time < datetime.now() - timedelta(seconds=60 * error_not_on_worker_timeout):
                print time.ctime(), "Crawl {} not found on worker error; crawl.scheduled_on_worker_time: {}; now: {}".format(crawl.id, crawl.scheduled_on_worker_time, datetime.now())
                error_crawl_ids.append((crawl.id, True, 'not found on worker'))
                continue

        if not job:
            continue

        if status != status_map[crawl.status]:
            if crawl.scheduled_on_worker_time < datetime.now() - timedelta(seconds=60 * error_started_timeout):
                print time.ctime(), "Crawl {} incorrect status on worker error: db - {}, worker - {} ({}); crawl.scheduled_on_worker_time: {}; now: {}".format(crawl.status, status_map[crawl.status], status, crawl.id, crawl.scheduled_on_worker_time, datetime.now())
                error_crawl_ids.append((crawl.id, False, 'incorrect status on worker: {}'.format(status)))
                continue
    return error_crawl_ids


def get_active_crawls_with_status(db_session, status):
    spiders = _get_active_spiders_map(db_session)
    spider_ids = spiders.keys()

    crawls = db_session.query(Crawl).filter(Crawl.status == status)\
        .filter(Crawl.spider_id.in_(spider_ids))
    return crawls


def get_scheduled_on_worker_crawls(db_session):
    return get_active_crawls_with_status(db_session, 'scheduled_on_worker')


def check_failed_scheduled_on_worker_crawls(db_session):
    crawls = get_scheduled_on_worker_crawls(db_session)
    error_crawl_ids = get_failed_crawls_scheduled_on_worker(db_session, crawls)

    for crawl_id, should_retry, error_msg in error_crawl_ids:
        db_session.commit()
        crawl = db_session.query(Crawl).get(crawl_id)
        if crawl.status != 'scheduled_on_worker':
            continue
        spider = db_session.query(Spider).get(crawl.spider_id)
        if not should_retry or not SpiderRetryManager.retry_spider(db_session, crawl_id, error_msg):
            print time.ctime(), "Found spider {} with crawl issue: {}".format(spider.name, error_msg)
            crawl.status = 'schedule_errors'
            path_errors = os.path.join(DATA_DIR, '%s_errors.csv' % crawl.id)
            export_errors(path_errors, [(0, error_msg)])
            db_session.add(crawl)
        else:
            print time.ctime(), "Retrying spider {} with crawl issue: {}".format(spider.name, error_msg)
        db_session.commit()


if __name__ == '__main__':
    db_session = Session()

    check_failed_scheduled_on_worker_crawls(db_session)

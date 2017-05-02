# -*- coding: utf-8 -*-
import sys
import os
import time
from datetime import datetime, timedelta

from check_for_failed_scheduled_on_worker_spiders import get_crawl_status_on_worker, status_map, \
    get_active_crawls_with_status

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE, '..')))
sys.path.append(os.path.abspath(os.path.join(HERE, '../..')))
sys.path.append(os.path.abspath(os.path.join(HERE, '../../productspidersweb')))
from productspidersweb.models import Spider, Crawl
sys.path.append('..')

from product_spiders.spiderretrymanager import SpiderRetryManager
from product_spiders.export import export_errors
from product_spiders.config import DATA_DIR

from db import Session

error_not_on_worker_timeout = 1  # 15 minutes
error_finished_timeout = 1  # 15 minutes
error_scheduled_timeout = 1  # 15 minutes


def get_failed_crawls_running(db_session, crawls):
    error_crawl_ids = []

    for crawl in crawls:
        if not crawl.jobid:
            continue
        spider = db_session.query(Spider).get(crawl.spider_id)

        status, job = get_crawl_status_on_worker(db_session, spider, crawl)

        if not status:
            if crawl.start_time < datetime.now() - timedelta(seconds=60 * error_not_on_worker_timeout):
                error_crawl_ids.append((crawl.id, True, 'not found on worker'))
                continue

        if status != status_map[crawl.status]:
            if status == status_map['scheduled_on_worker']:
                error_crawl_ids.append((crawl.id, False, 'crawl is scheduled on worker, while should be running'))
            if status == 'finished':
                if crawl.end_time < datetime.now() - timedelta(seconds=60 * error_finished_timeout):
                    error_crawl_ids.append((crawl.id, False,
                                            'crawl is finished on worker, but it\'s status is running in db'))
                    continue
    return error_crawl_ids


def get_running_crawls(db_session):
    return get_active_crawls_with_status(db_session, 'running')


def check_failed_running_crawls(db_session):
    crawls = get_running_crawls(db_session)
    error_crawl_ids = get_failed_crawls_running(db_session, crawls)

    for crawl_id, should_retry, error_msg in error_crawl_ids:
        db_session.commit()
        crawl = db_session.query(Crawl).get(crawl_id)
        if crawl.status != 'running':
            continue
        spider = db_session.query(Spider).get(crawl.spider_id)
        if not should_retry or not SpiderRetryManager.retry_spider(db_session, crawl_id, error_msg):
            print time.ctime(), "Found spider {} with crawl issue: {}".format(spider.name, error_msg)
            crawl.status = 'errors_found'
            crawl.end_time = db_session.execute(func.current_timestamp()).scalar()
            path_errors = os.path.join(DATA_DIR, '%s_errors.csv' % crawl.id)
            export_errors(path_errors, [(0, error_msg)])
            db_session.add(crawl)
        else:
            print time.ctime(), "Retrying spider {} with crawl issue: {}".format(spider.name, error_msg)
        db_session.commit()


if __name__ == '__main__':
    db_session = Session()

    check_failed_running_crawls(db_session)

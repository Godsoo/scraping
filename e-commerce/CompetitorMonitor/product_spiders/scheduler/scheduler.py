# -*- coding: utf-8 -*-
import random
import os.path
from time import ctime
from datetime import time
from time import gmtime

import requests
from sqlalchemy import and_

from productspidersweb.models import Spider, Account, WorkerServer, Crawl
from product_spiders.utils import is_cron_today
from product_spiders.dateutils import gmt_datetime, gmt_date
from product_spiders.dateutils import timezone_datetime, timezone_date
from product_spiders.export import export_errors
from product_spiders.config import DATA_DIR


DEFAULT_TZ = 'Europe/London'
GMT_TZ = 'GMT'


def crawl_required(spider):
    tz = GMT_TZ
    if spider.timezone:
        tz = spider.timezone

    gmt_now = gmtime()

    if not spider.enabled or not spider.account.enabled:
        return False

    # check for a cron specification
    if spider.crawl_cron and not is_cron_today(*spider.crawl_cron.split()[2:]):
        return False

    # check for the hour
    t = timezone_datetime(gmt_now, tz)
    if t.hour < spider.start_hour or (t.hour == spider.start_hour and t.minute < spider.start_minute):
        return False

    last_crawl = spider.crawls[-1] if spider.crawls else None
    if ((spider.account.crawls_per_day and spider.account.crawls_per_day > 1) or
            (spider.crawls_per_day and spider.crawls_per_day > 1)) and spider.enable_multicrawling:
        if last_crawl and last_crawl.status != 'upload_finished':
            return False

        crawls_per_day = spider.crawls_per_day
        if not crawls_per_day or (crawls_per_day and crawls_per_day <= 1):
            crawls_per_day = spider.account.crawls_per_day
        start = spider.start_hour * 60 * 60 + spider.start_minute * 60
        period = ((24 * 60 * 60) - start) / crawls_per_day
        crawls_today = [c for c in spider.crawls if c.crawl_date == timezone_date(gmt_now, tz)]
        if len(crawls_today) >= crawls_per_day:
            return False

        if start + period * len(crawls_today) >= (t.hour * 60 * 60) + (t.minute * 60) + t.second:
            return False
    else:
        if last_crawl and (timezone_date(gmt_now, tz) == last_crawl.crawl_date or
                                   last_crawl.status != 'upload_finished'):
            return False

    return True

def upload_required(spider):
    tz = GMT_TZ
    if spider.timezone:
        tz = spider.timezone

    gmt_now = gmtime()

    if not spider.enabled or not spider.account.enabled:
        return False

    if not spider.automatic_upload:
        return False

    last_crawl = spider.crawls[-1] if spider.crawls else None
    if not last_crawl:
        return False
    if last_crawl.status not in ('processing_finished', 'upload_errors'):
        return False

    # check for the hour
    if timezone_datetime(gmt_now, tz).hour < spider.upload_hour\
       and timezone_date(gmt_now, tz) == last_crawl.crawl_date:
        return False

    return True


def run_spider(spider_name, scrapy_url, concurrent_requests=None, priority=None, disable_cookies=False):
    print disable_cookies
    url = scrapy_url + 'schedule.json'
    args = [('project', 'default'), ('spider', spider_name)]
    if concurrent_requests:
        args.append(('setting', 'CONCURRENT_REQUESTS=%s' % concurrent_requests))
        args.append(('setting', 'CONCURRENT_REQUESTS_PER_DOMAIN=%s' % concurrent_requests))
    else:
        args.append(('setting', 'DOWNLOAD_DELAY=2'))

    if disable_cookies:
        args.append(('setting', 'COOKIES_ENABLED=0'))

    if priority:
        args.append(('priority', str(priority)))

    print args

    # adhoc
    if spider_name == 'eglobalcentral_co_it':
        args.append(('setting', 'DOWNLOAD_DELAY=30'))

    res = requests.post(url, data=args)
    print res.content
    return res.json()


def get_jobs_list(scrapy_url, tries=5):
    url = scrapy_url + 'listjobs.json' + "?project=default"
    tri = 0
    while tri < tries:
        try:
            res = requests.get(url)
        except requests.exceptions.RequestException:
            tri += 1
        else:
            return res.json()

    return None


def schedule_spiders(db_session, spider_names=None, force_run=False, launch=True):
    """ Creates crawls for spiders, which need crawl, and adds to queue """
    if not spider_names:
        spiders = db_session.query(Spider).join(Account)\
            .filter(and_(Spider.enabled == True, Account.enabled == True)).all()
    else:
        spiders = db_session.query(Spider)\
            .filter(and_(Spider.enabled == True, Account.enabled == True,
                         Spider.name.in_(spider_names))).all()
    spiders = sorted(spiders, key=lambda s: s.priority, reverse=True)
    for spider in spiders:
        tz = GMT_TZ
        if spider.timezone:
            tz = spider.timezone
        if force_run or (crawl_required(spider) and (spider_names is None or spider.name in spider_names)):
            print ctime(), "Scheduling spider '{}'".format(spider.name)
            server = None
            if spider.worker_server_id:
                server = db_session.query(WorkerServer).filter(and_(WorkerServer.id == spider.worker_server_id,
                                                                    WorkerServer.enabled == True)).first()
            crawl = Crawl(timezone_date(gmtime(), tz), spider)
            crawl.status = 'scheduled'
            if server:
                crawl.worker_server_id = server.id
            now = gmtime()
            crawl.crawl_time = time(hour=now.tm_hour, minute=now.tm_min, second=now.tm_sec)
            crawl.scheduled_time = gmt_datetime(gmtime())
            db_session.add(crawl)
            db_session.commit()
            db_session.add(crawl)
            db_session.commit()

    if launch:
        schedule_crawls_on_workers(db_session)


def reschedule_crawls(db_session):
    """ Readds "retry" crawls to queue """
    crawls = db_session.query(Crawl).filter(Crawl.retry == True)
    for crawl in crawls:
        spider = db_session.query(Spider).get(crawl.spider_id)
        account = db_session.query(Account).get(spider.account_id)
        tz = GMT_TZ
        if spider.timezone:
            tz = spider.timezone
        if spider.enabled and account.enabled:
            print ctime(), "Rescheduling spider '{}'".format(spider.name)
            server = None
            if spider.worker_server_id:
                server = db_session.query(WorkerServer).filter(and_(WorkerServer.id == spider.worker_server_id,
                                                                    WorkerServer.enabled == True)).first()

            crawl.crawl_date = timezone_date(gmtime(), tz)
            crawl.status = 'scheduled'
            crawl.products_count = 0
            crawl.changes_count = 0
            crawl.additions_count = 0
            crawl.deletions_count = 0
            crawl.updates_count = 0
            crawl.additional_changes_count = 0
            crawl.start_time = None
            crawl.end_time = None
            crawl.error_message = None
            crawl.jobid = None
            crawl.retry = False
            if server:
                crawl.worker_server_id = server.id
            else:
                crawl.worker_server_id = None
            crawl.scheduled_on_worker_time = None
            now = gmtime()
            crawl.crawl_time = time(hour=now.tm_hour, minute=now.tm_min, second=now.tm_sec)
            db_session.add(crawl)
            db_session.commit()
            db_session.add(crawl)
            db_session.commit()


def _get_worker_servers_running_slots(db_session):
    wss = db_session.query(WorkerServer).filter(WorkerServer.enabled == True)
    result = {}
    for ws in wss:
        jobs_list = get_jobs_list(ws.scrapy_url)
        if jobs_list is None:
            # server does not respond
            continue
        running_crawls = get_jobs_list(ws.scrapy_url)['running']
        pending_crawls = get_jobs_list(ws.scrapy_url)['pending']
        running_crawls_count = len(running_crawls)
        pending_crawls_count = len(pending_crawls)
        if running_crawls_count + pending_crawls_count < ws.worker_slots:
            result[ws.id] = ws.worker_slots - running_crawls_count - pending_crawls_count

    return result


def _get_scheduled_sorted_crawls(db_session):
    crawls = db_session.query(Crawl).filter(Crawl.status == 'scheduled').all()
    if not crawls:
        return []
    spider_ids = list({c.spider_id for c in crawls})
    spiders = db_session.query(Spider).filter(Spider.id.in_(spider_ids)).all()
    spiders_priority = {s.id: s.priority for s in spiders}
    spiders_multicrawling = {s.id: s.enable_multicrawling for s in spiders}
    # first sort by crawl time in ascending order - earliest must be in top
    crawls = sorted(crawls, key=lambda c: c.crawl_time)
    # then sort by priority - priority should have higher preference then crawl time
    crawls = sorted(crawls, key=lambda c: spiders_priority[c.spider_id], reverse=True)
    # then sort by multicrawling - multicrawl spiders should have highest priority
    crawls = sorted(crawls, key=lambda c: spiders_multicrawling[c.spider_id], reverse=True)
    return crawls


class SchedulingError(Exception):
    pass


def _schedule_regular_crawl(spider, server):
    res = run_spider(
        spider.name,
        server.scrapy_url,
        concurrent_requests=spider.concurrent_requests, priority=spider.priority,
        disable_cookies=spider.disable_cookies)
    try:
        jobid = res['jobid']
    except KeyError:
        raise SchedulingError("Error scheduling spider {} on worker. Response: {}".format(spider.name, str(res)))
    else:
        return jobid


def schedule_crawls_on_workers(db_session):
    """ Schedules crawls from queue to available worker servers """
    worker_slots = _get_worker_servers_running_slots(db_session)
    if not worker_slots:
        return
    crawls = _get_scheduled_sorted_crawls(db_session)
    if not crawls:
        return
    workers = {w.id: w for w in db_session.query(WorkerServer)}
    spiders = {}

    for crawl in crawls:
        predefined_server = crawl.worker_server_id and crawl.worker_server_id in workers
        # not free slots on predefined worker
        if predefined_server and crawl.worker_server_id not in worker_slots:
            continue
        if predefined_server:
            server = workers.get(crawl.worker_server_id)
        else:
            # pick random server
            server_id = random.choice(worker_slots.keys())
            server = workers.get(server_id)

        if crawl.spider_id not in spiders:
            spiders[crawl.spider_id] = db_session.query(Spider).get(crawl.spider_id)
        spider = spiders[crawl.spider_id]
        # change status to "scheduled_on_worker" before launching on worker
        # because worker will search the crawl by status "scheduled_on_worker"
        # so there is a race condition if worker already starts running spider
        # but this function have not yet commited crawl with "scheduled_on_worker" status to database
        # need to commit so session would load fresh data from db
        db_session.commit()
        # to avoid race condition
        crawl = db_session.query(Crawl).get(crawl.id)
        if crawl.status != 'scheduled':
            continue
        crawl.worker_server_id = server.id
        crawl.status = 'scheduled_on_worker'
        crawl.scheduled_on_worker_time = gmt_datetime(gmtime())
        db_session.add(crawl)
        db_session.commit()
        # scheduled on this server
        try:
            jobid = _schedule_regular_crawl(spider, server)
        except SchedulingError as e:
            msg = e.message
            crawl.status = 'schedule_errors'
            path_errors = os.path.join(DATA_DIR, '%s_errors.csv' % crawl.id)
            export_errors(path_errors, [(0, msg)])
        else:
            crawl.jobid = jobid

        db_session.add(crawl)
        db_session.commit()

        worker_slots[server.id] -= 1
        if worker_slots[server.id] < 1:
            del(worker_slots[server.id])

        # break if no more free slots
        if not worker_slots:
            break

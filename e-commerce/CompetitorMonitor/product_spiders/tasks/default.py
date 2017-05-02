# -*- coding: utf-8 -*-
import os
import time
import urllib
import json
from celery import task

from datetime import datetime, date, timedelta

from sqlalchemy import desc
from sqlalchemy.sql import text

from productspidersweb.models import (
    DailyErrors,
    Spider,
    SpiderError,
    Crawl,
    ERROR_TYPES,
    Developer,
    Account,
)
from db import Session

import config
from emailnotifier import EmailNotifier


HERE = os.path.abspath(os.path.dirname(__file__))
TOR_FILENAME = os.path.join(HERE, 'torinstances_restarted')
PROXY_CHECKED_FILENAME = os.path.join(HERE, 'proxy_checked')
ERROR_TYPES_DICT = dict(ERROR_TYPES)


def already_run(hours, filename):
    if os.path.exists(filename):
        file_gmtime = time.gmtime(os.path.getmtime(filename))
        f_dt = datetime.fromtimestamp(time.mktime(file_gmtime))
        if (datetime.utcnow() - f_dt) < timedelta(hours=hours):
            return True
    return False


@task
def restart_tor():
    if not already_run(2, TOR_FILENAME):
        from scripts.torinstances import restart_all
        restart_all()
        open(TOR_FILENAME, 'w').close()

@task
def crawler_report(receivers):
    db_session = Session()
    # Total # of real and possible errors in the past 7 days
    today = date.today()
    to_ = today
    from_ = today - timedelta(days=6)
    daily_errors = db_session.query(DailyErrors).filter(DailyErrors.date.between(from_, to_)).order_by(DailyErrors.date)
    total_real_errors = 0
    total_possible_errors = 0
    for daily_stat in daily_errors:
        total_real_errors += int(daily_stat.real if daily_stat.real else 0)
        total_possible_errors += int(daily_stat.possible if daily_stat.possible else 0)
    # Average number of possible errors we had over the past 7 days
    possible_errors_avg = int(round(float(total_possible_errors) / float(7)))
    # Current number of real errors in the system
    current_real_errors_count = db_session.query(Spider)\
        .join(SpiderError).filter(SpiderError.status == 'real').count()
    # Top 5 sites With Errors
    spider_errors = db_session.query(SpiderError)\
        .filter(SpiderError.time_added < today,
                SpiderError.time_added >= (today - timedelta(days=30)))\
        .order_by(SpiderError.time_added)
    spiders_total_errors = {}
    error_types_total = {}
    for spider_error in spider_errors:
        if spider_error.spider_id not in spiders_total_errors:
            spiders_total_errors[spider_error.spider_id] = 1
        else:
            spiders_total_errors[spider_error.spider_id] += 1
        if spider_error.error_type != 'awaiting_feedback':
            if spider_error.error_type not in error_types_total:
                error_types_total[spider_error.error_type] = 1
            else:
                error_types_total[spider_error.error_type] += 1
    top_five_spiders = sorted(spiders_total_errors.items(), key=lambda item: item[1], reverse=True)[:5]
    top_five_types = sorted(error_types_total.items(), key=lambda item: item[1], reverse=True)[:5]

    conn = db_session.connection()

    current_day = from_
    total_last_updated_sites = 0
    while current_day <= today:
        last_updated_sites = conn.execute(text('select count(s.id) from spider s join account a on(s.account_id = a.id) '
            'where s.enabled and (s.crawl_cron is null or s.crawl_cron = \'* * * * *\') and a.enabled and s.id in (select c.spider_id from crawl c join spider s2 on '
            '(c.spider_id = s2.id) join account a2 on (s2.account_id = a2.id) where s2.enabled and a2.enabled '
            'and c.status = \'upload_finished\' and c.end_time < :current_day group by c.spider_id having '
            'date_part(\'day\', :current_day - max(c.end_time)) >= 2);'), current_day=current_day).fetchone()
        total_last_updated_sites += int(last_updated_sites['count'])
        current_day += timedelta(days=1)
    last_updated_sites_avg = int(round(float(total_last_updated_sites) / float(7)))

    body = u'Here an overview about the crawlers status:\n\n'
    body += u'- Total # of Real Errors: %s' % total_real_errors
    body += u'\n- # Real Errors: %s' % current_real_errors_count
    body += u'\n- Average # of Possible Errors: %s' % possible_errors_avg
    body += u'\n- Top 5 sites With Errors:'
    for i, (sid, total) in enumerate(top_five_spiders):
        spider_name = db_session.query(Spider).get(sid).name
        body += u'\n\t%s. %s (%s)' % (i + 1, spider_name, total)
    body += '\n- Top 5 Errors Types'
    for i, (tid, total) in enumerate(top_five_types):
        type_name = ERROR_TYPES_DICT[tid]
        body += u'\n\t%s. %s (%s)' % (i + 1, type_name, total)
    body += '\n- Average # Of sites Not updated in 48 hours: %s' % last_updated_sites_avg

    notifier = EmailNotifier(config.SMTP_USER, config.SMTP_PASS,
                             config.SMTP_FROM, config.SMTP_HOST,
                             config.SMTP_PORT)
    notifier.send_notification(receivers, 'Crawlers Weekly Report', body)

    db_session.close()

@task
def sites_not_uploaded(filename='sites_not_uploaded'):
    db_session = Session()
    conn = db_session.connection()

    sites_not_uploaded_list = []
    if os.path.exists(filename):
        with open(filename) as f:
            for site in f:
                try:
                    sites_not_uploaded_list.append(int(site.strip()))
                except:
                    continue

    all_not_uploaded_sites = conn.execute(text(
        'select s.id, s.website_id, s.name, s.not_uploaded_alert_receivers '
        'from spider s join account a on(s.account_id = a.id) '
        'where s.enabled and a.enabled and s.id in (select c.spider_id from crawl c join spider s2 on '
        '(c.spider_id = s2.id) join account a2 on (s2.account_id = a2.id) where s2.enabled and a2.enabled '
        'and c.status = \'upload_finished\' group by c.spider_id having date_part(\'day\', now() - max(c.end_time)) >= 2);'))

    with open(filename, 'w') as f:
        for s in all_not_uploaded_sites:
            f.write('%s\n' % s['website_id'])

            last_successful_crawl = db_session.query(Crawl)\
                    .filter(Crawl.spider_id == s['id'], Crawl.status == 'upload_finished')\
                    .order_by(desc(Crawl.crawl_date)).first()
            if last_successful_crawl and last_successful_crawl.end_time:
                duration_error_state = datetime.now() - last_successful_crawl.end_time
            else:
                duration_error_state = None

            if duration_error_state and duration_error_state > timedelta(days=2)\
                and s['website_id'] not in sites_not_uploaded_list:

                    if s['not_uploaded_alert_receivers']:
                        receivers = [r.strip() for r in s['not_uploaded_alert_receivers'].split(',')]
                        body = u'%s last uploaded %s days ago\n' % (s['name'], duration_error_state.days)

                        notifier = EmailNotifier(config.SMTP_USER, config.SMTP_PASS,
                                                 config.SMTP_FROM, config.SMTP_HOST,
                                                 config.SMTP_PORT)
                        notifier.send_notification(receivers, 'Spider has not uploaded for 2 or more days', body)

    db_session.close()


@task
def sites_not_uploaded_account(receivers, account_id, subject, hours=48):
    db_session = Session()

    sites_not_uploaded_list = []

    spiders = db_session.query(Spider)\
        .filter(Spider.account_id == int(account_id),
                Spider.enabled == True)

    for spider in spiders:

        last_crawl = db_session.query(Crawl)\
            .filter(Crawl.spider_id == spider.id)\
            .order_by(Crawl.crawl_date.desc(),
                      desc(Crawl.id)).limit(1).first()

        last_successful_crawl = db_session.query(Crawl)\
            .filter(Crawl.spider_id == spider.id,
                    Crawl.status == 'upload_finished')\
            .order_by(Crawl.crawl_date.desc(),
                      desc(Crawl.id)).limit(1).first()
        if last_successful_crawl and last_successful_crawl.end_time:
            duration_error_state = datetime.now() - last_successful_crawl.end_time
        else:
            duration_error_state = None

        if duration_error_state and duration_error_state >= timedelta(hours=hours):
            last_updated = last_successful_crawl.crawl_date
            if spider.error and spider.error.status != 'fixed':
                if spider.error.error_desc:
                    real_error = spider.error.error_desc
                else:
                    real_error = ERROR_TYPES_DICT[spider.error.error_type]
                if spider.error.assigned_to_id:
                    assigned_to = db_session.query(Developer).get(spider.error.assigned_to_id)
                else:
                    assigned_to = None
            else:
                real_error = ''
                assigned_to = None

            sites_not_uploaded_list.append({
                'spider_name': spider.name,
                'last_uploaded': last_updated.strftime("%d-%m-%Y"),
                'error_type': real_error,
                'assigned_to': assigned_to.name if assigned_to else '',
                'status': last_crawl.status,
            })

    body = ''

    for site_data in sites_not_uploaded_list:
        body += (u'%(spider_name)s: Last Uploaded %(last_uploaded)s\n'
                u'- Error Type: %(error_type)s\n'
                u'- Status: %(status)s\n\n') % site_data

    if not sites_not_uploaded_list:
        body = u'All spiders have been uploaded'

    notifier = EmailNotifier(config.SMTP_USER, config.SMTP_PASS,
                             config.SMTP_FROM, config.SMTP_HOST,
                             config.SMTP_PORT)
    notifier.send_notification(receivers, subject, body)

    db_session.close()


@task
def sites_not_uploaded_account_2(receivers, account_id, subject):
    db_session = Session()

    sites_not_uploaded_list = []

    spiders = db_session.query(Spider)\
        .filter(Spider.account_id == int(account_id),
                Spider.enabled == True)

    for spider in spiders:

        last_crawl = db_session.query(Crawl)\
            .filter(Crawl.spider_id == spider.id)\
            .order_by(Crawl.crawl_date.desc(),
                      desc(Crawl.id)).limit(1).first()

        last_successful_crawl = db_session.query(Crawl)\
            .filter(Crawl.spider_id == spider.id,
                    Crawl.status == 'upload_finished')\
            .order_by(Crawl.crawl_date.desc(),
                      desc(Crawl.id)).limit(1).first()

        if last_crawl.status != 'upload_finished':
            last_updated = last_successful_crawl.crawl_date
            if spider.error and spider.error.status != 'fixed':
                if spider.error.error_desc:
                    real_error = spider.error.error_desc
                else:
                    real_error = ERROR_TYPES_DICT[spider.error.error_type]
                if spider.error.assigned_to_id:
                    assigned_to = db_session.query(Developer).get(spider.error.assigned_to_id)
                else:
                    assigned_to = None
            else:
                real_error = ''
                assigned_to = None

            sites_not_uploaded_list.append({
                'spider_name': spider.name,
                'last_uploaded': last_updated.strftime("%d-%m-%Y"),
                'error_type': real_error,
                'assigned_to': assigned_to.name if assigned_to else '',
                'status': last_crawl.status,
            })

    body = ''

    for site_data in sites_not_uploaded_list:
        body += (u'Spider: %(spider_name)s\n'
                 u'Status: %(status)s\n'
                 u'Last Upload: %(last_uploaded)s\n'
                 u'Errors Type: %(error_type)s\n'
                 u'Dev: %(assigned_to)s\n\n') % site_data

    if not sites_not_uploaded_list:
        body = u'All spiders have been uploaded'

    notifier = EmailNotifier(config.SMTP_USER, config.SMTP_PASS,
                             config.SMTP_FROM, config.SMTP_HOST,
                             config.SMTP_PORT)
    notifier.send_notification(receivers, subject, body)

    db_session.close()


@task
def check_failing_proxies_alert(proxy_list, url='http://news.ycombinator.com', receivers=['emr.frei@gmail.com']):
    if not already_run(6, PROXY_CHECKED_FILENAME):
        open(PROXY_CHECKED_FILENAME, 'w').close()

        check_proxy_list = []
        for proxy_url in proxy_list:
            try:
                urllib.urlopen(url, proxies={'http': proxy_url})
            except IOError:
                check_proxy_list.append(proxy_url)
            else:
                time.sleep(1)

        if check_proxy_list:

            body = ''
            for proxy_url in check_proxy_list:
                body += '%s\n' % proxy_url

            notifier = EmailNotifier(config.SMTP_USER, config.SMTP_PASS,
                                     config.SMTP_FROM, config.SMTP_HOST,
                                     config.SMTP_PORT)
            notifier.send_notification(receivers, 'Proxy Service - check proxy list', body)


from product_spiders.utils import is_cron_today

@task
def send_bsm_missing_full_run_alert(receivers):
    db_session = Session()

    spiders = db_session.query(Spider)\
        .join(Account)\
        .filter(Account.enabled == True,
                Spider.enabled == True,
                Spider.parse_method == 'BSM')

    yesterday_date = (datetime.today() - timedelta(days=1)).date()

    for spider in spiders:
        last_crawl = db_session.query(Crawl)\
            .filter(Crawl.spider_id == spider.id)\
            .order_by(Crawl.id.desc(),
                      Crawl.crawl_date.desc())\
            .limit(1)\
            .first()
        if not last_crawl:
            continue
        if not last_crawl.crawl_date:
            continue
        if last_crawl.crawl_date < yesterday_date:
            continue
        if spider.crawl_method2 and spider.crawl_method2.crawl_method == 'BigSiteMethod':
            if spider.crawl_method2._params:
                bsm_params = spider.crawl_method2.params
                if 'full_crawl_cron' not in bsm_params:
                    continue
                dom, m, dow = bsm_params['full_crawl_cron'].split()
                if is_cron_today(dom, m, dow, dt=yesterday_date):
                    yesterday_crawl = db_session.query(Crawl)\
                        .filter(Crawl.spider_id == spider.id,
                                Crawl.crawl_date == yesterday_date)\
                        .limit(1)\
                        .first()
                    if not yesterday_crawl:
                        account = db_session.query(Account).get(spider.account_id)
                        body = u'Missing full run for spider with BSM enabled.\n\n'
                        body += u'Account name: %s\n' % account.name
                        body += u'Spider name: %s\n' % spider.name
                        body += u'Missing full run date: %s\n' % unicode(yesterday_date)
                        notifier = EmailNotifier(config.SMTP_USER, config.SMTP_PASS,
                                                 config.SMTP_FROM, config.SMTP_HOST,
                                                 config.SMTP_PORT)
                        notifier.send_notification(receivers, '[WARNING] - Missing full run for Spider', body)

    db_session.close()


@task
def send_bsm_missing_full_run_one_month_alert(receivers):
    db_session = Session()

    spiders = db_session.query(Spider)\
        .join(Account)\
        .filter(Account.enabled == True,
                Spider.enabled == True,
                Spider.parse_method == 'BSM')

    today_date = datetime.today().date()
    one_month_ago_date = datetime(
        day=today_date.day,
        month=(today_date.month - 1 if today_date.month != 1 else 12),
        year=(today_date.year -1 if today_date.month == 1 else today_date.year)
    ).date()

    for spider in spiders:
        last_full_run_date = None
        spider_crawls = db_session.query(Crawl)\
            .filter(Crawl.spider_id == spider.id)\
            .order_by(Crawl.crawl_date.desc())
        for crawl in spider_crawls:
            if crawl.stats and crawl.stats.stats_json:
                crawl_stats = json.loads(crawl.stats.stats_json)
                if crawl_stats.get('BSM', False) and crawl_stats['full_run']:
                    last_full_run_date = crawl.crawl_date
                    break
        if last_full_run_date and (last_full_run_date < one_month_ago_date):
            account = db_session.query(Account).get(spider.account_id)
            body = u'Very old full run for spider with BSM enabled.\n\n'
            body += u'Account name: %s\n' % account.name
            body += u'Spider name: %s\n' % spider.name
            body += u'Last full run date: %s\n' % unicode(last_full_run_date)
            notifier = EmailNotifier(config.SMTP_USER, config.SMTP_PASS,
                                     config.SMTP_FROM, config.SMTP_HOST,
                                     config.SMTP_PORT)
            notifier.send_notification(receivers, '[WARNING] - Very old full run for Spider', body)

    db_session.close()

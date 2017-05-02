import os
import json
import csv
import sys
from datetime import datetime, timedelta, date
from decimal import Decimal
from collections import defaultdict

import urllib2
from tempfile import NamedTemporaryFile

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import FileResponse
from pyramid.security import Everyone
from sqlalchemy import desc

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HERE, '../..'))
sys.path.append(os.path.join(HERE, '../../zabbix/agents'))

from spider_stats import SpiderStatsDB, SDBSession, WORKER_SERVERS, SpiderStats

from models import DBSession, Spider, Account, WorkerServer, Crawl, CrawlHistory, CrawlStats

@view_config(route_name='server_stats', renderer='server_stats.mako', permission='administration')
def server_stats(request):
    return {}


@view_config(route_name='current_server_stats', renderer='json', permission='administration')
def current_server_stats(request):
    db_session = SDBSession()
    spider_stats = SpiderStatsDB(db_session)
    current_stats = spider_stats.get_current_stats()
    statuses = {'scheduled': [], 'running': [], 'errors': [], 'finished': []}
    categories = ['total'] + sorted([x for x in current_stats if x != 'total'])
    for x in categories:
        for s in statuses:
            statuses[s].append(current_stats[x][s])

    server_name = {'total': 'Total'}
    for server in WORKER_SERVERS:
        server_name[str(server['id'])] = server['name']

    res = {'categories': [server_name[str(c)] for c in categories]}
    res.update(statuses)
    return res

@view_config(route_name='current_spider_stats', renderer='json', permission='administration')
def current_spider_stats(request):
    db_session = DBSession()
    spider_stats = SpiderStats(db_session)
    stats = spider_stats.get_global_stats(WORKER_SERVERS)
    res = []
    spider_names = []
    for worker in WORKER_SERVERS:
        scheduled_on_worker = stats[worker['id']]['scheduled_on_worker']
        scheduled_on_worker_count = len(scheduled_on_worker)
        for i, s in enumerate(scheduled_on_worker):
            res.append({'pos': str(i + 1), 'spider': s['spider'], 'server': worker['name'],
                        'status': 'Scheduled on Worker', 'start_time': ''})
            spider_names.append(s['spider'])
        scheduled = stats[worker['id']]['scheduled']
        for i, spider_name in enumerate(scheduled):
            res.append({'pos': str(scheduled_on_worker_count + i + 1), 'spider': spider_name, 'server': worker['name'],
                        'status': 'Scheduled', 'start_time': ''})
            spider_names.append(spider_name)
        running = stats[worker['id']]['running']
        for s in running:
            start_time = s['start_time']
            if worker.get('delta_time'):
                start_time += worker['delta_time']

            res.append({'pos': '', 'spider': s['spider'], 'server': worker['name'], 'status': 'Running',
                        'start_time': str(start_time)})
            spider_names.append(s['spider'])

    scheduled = spider_stats.get_total_scheduled()
    scheduled = [spider_name for spider_name in scheduled if spider_name not in spider_names]
    for i, spider_name in enumerate(scheduled):
        res.append({'pos': str(i + 1), 'spider': spider_name, 'server': '',
                    'status': 'Scheduled', 'start_time': ''})
        spider_names.append(spider_name)

    accounts = db_session.query(Account.name.label('account'), Spider.name.label('spider'))\
                         .join(Spider).filter(Spider.name.in_(spider_names))
    accounts = {a.spider: a.account for a in accounts}
    for r in res:
        r['account'] = accounts.get(r['spider'], '')

    return res


@view_config(route_name='historical_server_stats', renderer='json', permission='administration')
def historical_server_stats(request):
    db_session = SDBSession()
    spider_stats = SpiderStatsDB(db_session)
    stats = spider_stats.get_historical_stats(from_=datetime.now() - timedelta(hours=23, minutes=59))
    statuses = {'scheduled': [], 'running': [], 'errors': [], 'finished': []}
    for stat in stats:
        data = stat['stats']
        date_ = int((stat['time'] - datetime(1970,1,1)).total_seconds()) * 1000
        for s in statuses:
            statuses[s].append([date_, data['total'][s]])

    return statuses

@view_config(route_name='app_stats', renderer='app_stats.mako', permission='administration')
def app_stats(request):
    return {}


def sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

@view_config(route_name='importer_stats', renderer='json', permission='administration')
def importer_stats(request):
    change_type = request.GET.get('type', '')
    res = urllib2.urlopen('https://app.competitormonitor.com/api/get_importer_stats.json?api_key=3Df7mNg').read()
    res = json.loads(res)
    res = res[change_type]
    formatted = []
    for r in res:
        r['size'] = sizeof_fmt(r['size'])
        if 'account' in r:
            formatted.append(r)

    return formatted

@view_config(route_name='spider_issues', renderer='spider_issues.mako', permission='administration')
def spider_issues(request):
    return {}

@view_config(route_name='scheduled_issues', renderer='json', permission='administration')
def scheduled_issues(request):
    db_session = DBSession()
    errors = open('/tmp/failed_scheduled').read().split('\n')
    errors = [e for e in errors if e]
    spiders = db_session.query(Spider, Account, WorkerServer)\
                        .join(Account).join(Crawl, Crawl.spider_id == Spider.id)\
                        .outerjoin(WorkerServer, Spider.worker_server_id == WorkerServer.id)\
                        .filter(Spider.name.in_(errors), Crawl.status == 'scheduled')
    result = []
    for spider in spiders:
        result.append({'account': spider.Account.name, 'spider': spider.Spider.name,
                       'url': '/productspiders/last_log_file?spider=' + spider.Spider.name,
                       'server': spider.WorkerServer.name if spider.WorkerServer else ''})

    return result

@view_config(route_name='restart_scheduled', renderer='json', permission='administration')
def restart_scheduled(request):
    db_session = DBSession()
    spiders = request.POST.get('spiders')
    spiders = json.loads(spiders)
    spiders = db_session.query(Spider).filter(Spider.name.in_(spiders)).all()
    spider_ids = [s.id for s in spiders]
    for spider_id in spider_ids:
        crawl = db_session.query(Crawl).filter(Crawl.spider_id == spider_id,
                                               Crawl.status == 'scheduled_on_worker').first()
        if crawl:
            db_session.query(CrawlStats).filter(CrawlStats.crawl_id == crawl.id).delete()
            db_session.query(CrawlHistory).filter(CrawlHistory.crawl_id == crawl.id).delete()
            db_session.query(Crawl).filter(Crawl.id == crawl.id).delete()

@view_config(route_name='spider_events', permission=Everyone)
def spider_events(request):
    db_session = DBSession()
    d = request.GET.get('date')
    if not d:
        return HTTPNotFound()

    try:
        d = d.split('-')
        d = date(year=int(d[0]), month=int(d[1]), day=int(d[2]))
    except Exception:
        return HTTPNotFound()

    q = db_session.query(Crawl, Spider, Account).join(Spider).join(Account)
    q = q.filter(Crawl.crawl_date == d).order_by(Crawl.start_time)
    f = NamedTemporaryFile(delete=False, suffix='.csv')
    writer = csv.writer(f)
    writer.writerow(['Spider', 'Account', 'Scheduled Start Time',
                     'Time Taken to Start', 'Actual Start Time',
                     'End Time',
                     'Time Taken', 'Upload Time'])

    def format_time(t):
        if not t:
            return ''
        else:
            return t.strftime('%Y-%m-%d %H:%M:%S')

    for res in q.yield_per(100):
        writer.writerow([res.Spider.name, res.Account.name, format_time(res.Crawl.scheduled_time),
                         str(res.Crawl.start_time - res.Crawl.scheduled_time).split('.')[0]
                         if res.Crawl.start_time and res.Crawl.scheduled_time else '',
                         format_time(res.Crawl.start_time), format_time(res.Crawl.end_time),
                         str(res.Crawl.end_time - res.Crawl.start_time).split('.')[0]
                         if res.Crawl.start_time and res.Crawl.end_time else '',
                         format_time(res.Crawl.uploaded_time)])
    f.close()
    r = FileResponse(f.name, request=request, content_type='text/csv')

    return r


def get_perc(total, changes):
    if not total:
        return Decimal(0)
    else:
        return (Decimal(changes) * 100) / Decimal(total)

def get_crawl_stats(crawl_id, path):
    field = defaultdict(int)
    with open(os.path.join(path, 'data/additional/{}_changes.json-lines'.format(crawl_id))) as f:
        for line in f:
            data = json.loads(line)
            for f in data['changes']:
                field[f] += 1
                field['total changes'] += 1

    return field


@view_config(route_name='additional_changes_stats', permission=Everyone)
def additional_changes_stats(request):
    db_session = DBSession()
    d = request.GET.get('date')
    if not d:
        return HTTPNotFound()

    try:
        d = d.split('-')
        d = date(year=int(d[0]), month=int(d[1]), day=int(d[2]))
    except Exception:
        return HTTPNotFound()

    spiders = db_session.query(Spider, Account).join(Account).filter(Spider.enabled == True,
                                                                     Account.enabled == True)
    final_stats = []

    for s in spiders.yield_per(50):
        try:
            crawl = db_session.query(Crawl).filter(Crawl.spider_id == s.Spider.id,
                                                   Crawl.status == 'upload_finished',
                                                   Crawl.crawl_date == d).order_by(desc(Crawl.id)).first()

            if crawl:
                stats = get_crawl_stats(crawl.id, '/home/innodev/product-spiders')
                row = {'account': s.Account.name, 'spider': s.Spider.name,
                       'total products': str(crawl.products_count),
                       'changes percentage': get_perc(crawl.products_count, stats['total changes'])}
                for k in stats:
                    row[k] = str(stats[k])

                final_stats.append(row)
        except Exception:
            continue

    final_stats.sort(cmp=lambda x, y: cmp(int(x['total changes']), int(y['total changes'])), reverse=True)
    f = NamedTemporaryFile(suffix='.csv', delete=False)
    header = ['account', 'spider', 'total products',
              'total changes', 'changes percentage', 'name', 'url',
              'image_url', 'category', 'brand', 'sku', 'stock',
              'shipping_cost', 'dealer', 'identifier']
    writer = csv.DictWriter(f, header)
    writer.writeheader()
    for row in final_stats:
        writer.writerow(row)
    f.close()
    r = FileResponse(f.name, request=request, content_type='text/csv')

    return r
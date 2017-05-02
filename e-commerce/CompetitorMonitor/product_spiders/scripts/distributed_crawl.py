import sys
import os
from urllib2 import urlopen
from urllib import urlencode
import json
from time import gmtime
from datetime import time

from sqlalchemy import desc, and_

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE,
                                             '../../productspidersweb')))

sys.path.append('..')

from productspidersweb.models import Spider, Crawl, WorkerServer


from db import Session
from scheduler import Scheduler
from dateutils import gmt_date



def run_spider(spider_name, scrapy_url, concurrent_requests=None):
    args = [('project', 'default'), ('spider', spider_name)]
    if concurrent_requests:
        args.append(('setting', 'CONCURRENT_REQUESTS=%s' % concurrent_requests))
        args.append(('setting', 'CONCURRENT_REQUESTS_PER_DOMAIN=%s' % concurrent_requests))
    else:
        args.append(('setting', 'DOWNLOAD_DELAY=2'))

    args = urlencode(args)

    res = urlopen(scrapy_url, args).read()
    print res
    return res

def run_crawls(db_session, spider_names=None):
    worker_servers = db_session.query(WorkerServer).filter(WorkerServer.enabled == True).all()
    i = 0
    spider_scheduler = Scheduler(db_session)
    for spider in db_session.query(Spider).order_by(desc(Spider.priority), desc(Spider.enable_multicrawling)).all():
        if spider_scheduler.crawl_required(spider) and (spider_names is None or spider.name in spider_names):
            server = None
            if spider.worker_server_id:
                server = db_session.query(WorkerServer).filter(and_(WorkerServer.id == spider.worker_server_id,
                                                                    WorkerServer.enabled == True)).first()
            if not server:
                server = worker_servers[i]
            crawl = Crawl(gmt_date(gmtime()), spider)
            crawl.status = 'scheduled'
            crawl.worker_server_id = server.id
            now = gmtime()
            crawl.crawl_time = time(hour=now.tm_hour, minute=now.tm_min, second=now.tm_sec)
            db_session.add(crawl)
            db_session.commit()

            res = run_spider(spider.name, server.scrapy_url, concurrent_requests=spider.concurrent_requests)
            if i < len(worker_servers) - 1:
                i += 1
            else:
                i = 0

            res = json.loads(res)
            crawl.jobid = res['jobid']
            db_session.add(crawl)
            db_session.commit()

if __name__ == '__main__':
    db_session = Session()
    spider_names = None
    if len(sys.argv) > 1:
        spider_names = sys.argv[1:]

    run_crawls(db_session, spider_names)


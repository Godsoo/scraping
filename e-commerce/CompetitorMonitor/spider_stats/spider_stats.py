import json
import sys
from datetime import datetime, date

from sqlalchemy import func
import requests
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column
from sqlalchemy import Integer, Text, ForeignKey, Date

Base = declarative_base()


class Spider(Base):
    __tablename__ = 'spider'
    id = Column(Integer, primary_key=True)
    name = Column(Text)


class Crawl(Base):
    __tablename__ = 'crawl'
    id = Column(Integer, primary_key=True)
    spider_id = Column(ForeignKey(Spider.id))
    status = Column(Text)
    crawl_date = Column(Date)
    worker_server_id = Column(Integer)

class SpiderStats(object):
    def __init__(self, db_session):
        self.db_session = db_session

    def _get_spiders_db(self, statuses, server=None):
        q = self.db_session.query(func.distinct(Spider.name)).join(Crawl)\
            .filter(Crawl.status.in_(statuses), Crawl.crawl_date == date.today())
        if server:
            q = q.filter(Crawl.worker_server_id == server['id'])
        else:
            q = q.filter(Crawl.worker_server_id == None)
        return q.all()

    def get_spider_stats(self, server):
        scrapy_url = server['scrapy_url']
        res = {'scheduled_on_worker': [], 'running': []}
        res['finished'] = self._get_spiders_db(['processing_finished', 'upload_finished', 'errors_found'], server)
        res['errors'] = self._get_spiders_db(['errors_found', 'retry'], server)
        res['scheduled'] = self._get_spiders_db(['scheduled'], server)
        r = requests.get(scrapy_url.rstrip('/') + '/listjobs.json?project=default')
        if r.status_code == 200:
            r = json.loads(r.text)
            res['scheduled_on_worker'] = r['pending']
            res['running'] = r['running']
            for spider in res['running']:
                if 'start_time' in spider:
                    spider['start_time'] = datetime.strptime(spider['start_time'].split('.')[0], '%Y-%m-%d %H:%M:%S')

        return res

    def get_global_stats(self, servers):
        res = {}
        for server in servers:
            stats = self.get_spider_stats(server)
            res[server['id']] = stats

        return res

    def get_total_scheduled(self):
        return [x[0] for x in self._get_spiders_db(['scheduled'])]

    def get_global_stats_summary(self, servers):
        stats = self.get_global_stats(servers)
        total = {}
        res = {}
        for server in stats:
            res[server] = {}
            stats[server]['scheduled'] += stats[server]['scheduled_on_worker']
            del(stats[server]['scheduled_on_worker'])
            for k in stats[server]:
                res[server][k] = len(stats[server][k])
                total[k] = total.get(k, 0) + res[server][k]

        total['scheduled'] = total.get('scheduled', 0) + len(self.get_total_scheduled())

        res['total'] = total
        return res

if __name__ == '__main__':
    pass
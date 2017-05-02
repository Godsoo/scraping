import os
from datetime import datetime, timedelta
import json

from sqlalchemy import Column
from sqlalchemy import UnicodeText
from sqlalchemy import DateTime, Integer
from sqlalchemy import desc

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

DBSession = scoped_session(sessionmaker())
Base = declarative_base()
HERE = os.path.dirname(os.path.abspath(__file__))
DB_URI = 'sqlite:///%s' % os.path.join(HERE, 'spider_stats.db')
DB_URI_SPIDERS = 'postgresql://productspiders:productspiders@localhost:5432/productspiders'


class HistoricalSpiderStats(Base):
    __tablename__ = 'spider_stats'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    stats = Column(UnicodeText)


def initialize_sql(engine):
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)


class SpiderStatsDB(object):
    def __init__(self, db_session):
        self.db_session = db_session

    def insert_historical_stats(self, stats, timestamp=None):
        t = timestamp
        if not timestamp:
            t = datetime.now()
        hstats = HistoricalSpiderStats()
        hstats.timestamp = t
        hstats.stats = json.dumps(stats)
        self.db_session.add(hstats)
        self.db_session.commit()

    def get_current_stats(self):
        r = self.db_session.query(HistoricalSpiderStats).order_by(desc(HistoricalSpiderStats.timestamp)).first()
        if r:
            return json.loads(r.stats)
        else:
            return None

    def get_historical_stats(self, from_=None, to=None):
        r = self.db_session.query(HistoricalSpiderStats)
        if from_:
            r = r.filter(HistoricalSpiderStats.timestamp >= from_)
        if to:
            r = r.filter(HistoricalSpiderStats.timestamp <= to)

        r = r.order_by(HistoricalSpiderStats.timestamp).all()
        res = []
        for x in r:
            res.append({'time': x.timestamp, 'stats': json.loads(x.stats)})

        return res


engine = create_engine(DB_URI)
SDBSession = sessionmaker(engine)
WORKER_SERVERS = [{'name': 'Slave 2', 'id': 10000005, 'scrapy_url': 'http://88.198.32.57:6805/',
                   'delta_time': -timedelta(minutes=60)},
                  {'name': 'Slave 1', 'id': 10000006, 'scrapy_url': 'http://competitormonitor.com:6805/',
                   'delta_time': timedelta(minutes=54)},
                  {'name': 'Slave 3', 'id': 10000010, 'scrapy_url': 'http://88.99.3.215:6805'},
                  {'name': 'Master', 'id': 10000007, 'scrapy_url': 'http://148.251.79.44:6805/'}]

if __name__ == '__main__':
    engine = create_engine(DB_URI)
    initialize_sql(engine)
    db_session = sessionmaker(engine)()

    spiders_engine = create_engine(DB_URI_SPIDERS)
    spiders_db_session = sessionmaker(spiders_engine)()

    from updater import SpiderStatsUpdater
    from spider_stats import SpiderStats
    spider_stats = SpiderStats(spiders_db_session)
    stats_db = SpiderStatsDB(db_session)
    upd = SpiderStatsUpdater(stats_db, spider_stats)
    upd.update_stats(WORKER_SERVERS)

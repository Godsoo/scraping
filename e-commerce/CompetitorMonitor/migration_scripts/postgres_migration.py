#!/usr/bin/env python

import getopt
import inspect
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sqlalchemy.exc

from productspidersweb.models import *

def make_session(connection_string):
    engine = create_engine(connection_string, echo=False, convert_unicode=True)
    Session = sessionmaker(bind=engine)
    return Session(), engine

def clone_object(o, table):
    argsn = len(inspect.getargspec(table.__init__).args) - 1
    args = [None] * argsn
    cl = table(*args)
    for c in o.__table__.columns._data.keys():
        setattr(cl, c, getattr(o, c))

    return cl


def copy_table(tbl_cls, src_session, dst_session):
    for r in src_session.query(tbl_cls):
        dst_session.add(clone_object(r, tbl_cls))

        try:
            dst_session.commit()
        except sqlalchemy.exc.IntegrityError:
            dst_session.rollback()
            continue

src_session = make_session('sqlite:////home/lucas/product-spiders/productspidersweb/productspidersweb.db')[0]
dst_session = make_session('postgresql://productspiders:productspiders@localhost:5432/productspiders')[0]

for tbl_cls in [Account, ProxyList, WorkerServer, Spider, NotificationReceiver, SpiderError, DeletionsReview]:
    print "copying table"
    copy_table(tbl_cls, src_session, dst_session)

spiders_all = src_session.query(Spider).all()
spiders = [s.id for s in spiders_all]

crawls = src_session.query(Crawl).all()
for crawl in crawls:
    if crawl.spider_id not in spiders:
        continue
    else:
        new_crawl = clone_object(crawl, Crawl)
        dst_session.add(new_crawl)

dst_session.commit()

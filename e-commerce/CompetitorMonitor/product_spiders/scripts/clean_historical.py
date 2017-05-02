import os
import sys

from sqlalchemy import desc

HERE = os.path.dirname(__file__)
sys.path.append(os.path.abspath(os.path.join(HERE, '../../productspidersweb')))

from productspidersweb.models import Crawl, Account, Spider
sys.path.append('..')

from db import Session

path = os.path.abspath(os.path.join(HERE, '../..'))

DATA_DIR = os.path.join(path, 'data')

def _delete_crawl_files(crawl_id):
    try:
        os.unlink(os.path.join(DATA_DIR, '%s_products.csv' % crawl_id))
    except OSError:
        pass
    try:
        os.unlink(os.path.join(DATA_DIR, '%s_changes.csv' % crawl_id))
    except OSError:
        pass

    try:
        os.unlink(os.path.join(DATA_DIR, '%s_changes_old.csv' % crawl_id))
    except OSError:
        pass
    try:
        os.unlink(os.path.join(DATA_DIR, '%s_changes_new.csv' % crawl_id))
    except OSError:
        pass
    try:
        os.unlink(os.path.join(DATA_DIR, 'meta/%s_meta.json' % crawl_id))
    except OSError:
        pass
    try:
        os.unlink(os.path.join(DATA_DIR, 'meta/%s_meta_changes.json' % crawl_id))
    except OSError:
        pass
    try:
        os.unlink(os.path.join(DATA_DIR, 'meta/%s_meta_changes.json-lines' % crawl_id))
    except OSError:
        pass
    try:
        os.unlink(os.path.join(DATA_DIR, 'additional/%s_changes.json' % crawl_id))
    except OSError:
        pass
    try:
        os.unlink(os.path.join(DATA_DIR, 'additional/%s_changes.json-lines' % crawl_id))
    except OSError:
        pass
    try:
        os.unlink(os.path.join(DATA_DIR, '%s_errors.csv' % crawl_id))
    except OSError:
        pass

db_session = Session()
accounts = db_session.query(Account).filter(Account.enabled == True).all()
print str(len(accounts)), "accounts to clean"

accounts = accounts[0]
for a in accounts:
    print "Account", a.name
    spiders = db_session.query(Spider).filter(Spider.account_id == a.id).all()
    for spider in spiders:
        print "Spider", spider.name
        print "Removing crawls"
        crawls = db_session.query(Crawl).filter(Crawl.spider_id == spider.id).all()
        crawls = [c for c in crawls if c.crawl_date.year < 2014]
        for crawl in crawls:
            _delete_crawl_files(crawl.id)
            #db_session.delete(crawl)
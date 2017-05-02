import os
import sys

from sqlalchemy import desc
import paramiko

HERE = os.path.dirname(__file__)
sys.path.append(os.path.abspath(os.path.join(HERE, '../../productspidersweb')))

from productspidersweb.models import Crawl, Account, Spider
sys.path.append('..')

from db import Session

path = os.path.abspath(os.path.join(HERE, '../..'))

DATA_DIR = os.path.join(path, 'data')

'''
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
        os.unlink(os.path.join(DATA_DIR, 'additional/%s_changes.json' % crawl_id))
    except OSError:
        pass
    try:
        os.unlink(os.path.join(DATA_DIR, '%s_errors.csv' % crawl_id))
    except OSError:
        pass
'''

def upload_crawl_files(crawl_id, sftp):
    files = ['%s_products.csv', '%s_changes.csv', '%s_changes_old.csv', 'meta/%s_meta.json',
             'meta/%s_meta_changes.json', 'additional/%s_changes.json', '%s_errors.csv',
             'meta/%s_meta.json-lines', 'meta/%s_meta_changes.json-lines',
             'meta/%s_meta_changes.json-lines', 'additional/%s_changes.json-lines', '%s_errors.csv',
    ]
    for f in files:
        full_name = os.path.join(DATA_DIR, f % crawl_id)
        if os.path.exists(full_name):
            sftp.put(full_name, full_name)

db_session = Session()
accounts = db_session.query(Account).filter(Account.enabled == True).all()
print str(len(accounts)), "Accounts to upload"

host = "148.251.79.44"
port = 22
transport = paramiko.Transport((host, port))

# Auth

password = "kl03yP455"
username = "innodev"
transport.connect(username=username, password=password)

sftp = paramiko.SFTPClient.from_transport(transport)

accounts = [accounts[0]]
for i, a in enumerate(accounts):
    print "Account", a.name, i
    spiders = db_session.query(Spider).filter(Spider.account_id == a.id).all()
    for spider in spiders:
        print "Spider", spider.name
        print "Uploading crawls"
        crawls = db_session.query(Crawl).filter(Crawl.spider_id == spider.id).order_by(desc(Crawl.crawl_date), desc(Crawl.id))\
                                                                             .limit(3).all()
        for crawl in crawls:
            print crawl.crawl_date
            upload_crawl_files(crawl.id, sftp)

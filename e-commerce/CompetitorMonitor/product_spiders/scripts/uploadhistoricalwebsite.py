import csv
import sys
import os
import tempfile
from datetime import datetime

from sqlalchemy import desc, and_
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE,
                                             '../../productspidersweb')))

from productspidersweb.models import Spider, Crawl, Account
sys.path.append('..')

from db import Session
from uploader import Uploader, UploaderException, upload_changes
from export import export_changes_new, export_additional_changes
from productsupdater import ProductsUpdater
import config

DATA_DIR = os.path.abspath(os.path.join(HERE, '../../data'))

if len(sys.argv) < 2:
    print "Usage %s <website id> [from date]"
    sys.exit(1)

from_date = None
if len(sys.argv) > 2:
    from_date = sys.argv[2]
    from_date = datetime.strptime(from_date, '%Y-%m-%d').date()

first_empty = False
if len(sys.argv) > 3 and sys.argv[3] == 'first_empty':
    first_empty = True

db_session = Session()
website_id = sys.argv[1]
spider = db_session.query(Spider).filter(Spider.website_id == website_id).first()
account = db_session.query(Account).get(spider.account_id)
crawls = db_session.query(Crawl)\
                   .filter(and_(Crawl.spider_id == spider.id, Crawl.status == 'upload_finished'))\
                   .order_by(Crawl.crawl_date).all()
if from_date:
    crawls = [c for c in crawls if c.crawl_date >= from_date]

updater = ProductsUpdater(db_session)
uploader = Uploader()
server_data = config.SERVERS['s2']
uploader.set_host_data(server_data['host'], server_data['user'], server_data['password'], server_data['port'])
for i, crawl in enumerate(crawls):
    previous_crawl = db_session.query(Crawl)\
                               .filter(and_(Crawl.spider_id == crawl.spider_id,
                                            Crawl.id < crawl.id))\
                                       .order_by(desc(Crawl.crawl_date)).first()

    old_products = []
    if previous_crawl and (i > 0 or not first_empty):
        with open(os.path.join(DATA_DIR, '%s_products.csv' % previous_crawl.id)) as f:
            reader = csv.DictReader(f)
            old_products = [row for row in reader]


    with open(os.path.join(DATA_DIR, '%s_products.csv' % crawl.id)) as f:
        reader = csv.DictReader(f)
        products = [row for row in reader]

    changes, additions, deletions, updates = updater.compute_changes(crawl.id, old_products, products,
                                                                     crawl.spider.silent_updates,
                                                                     set_crawl_data=False)

    path = os.path.join(tempfile.gettempdir(), '%s_changes.csv' % crawl.id)
    export_changes_new(path, changes, crawl.spider.website_id)

    additional_changes = updater.compute_additional_changes(crawl.id, old_products, products, set_crawl_data=False)
    additional_path = os.path.join(tempfile.gettempdir(), '%s_changes.json-lines' % crawl.id)
    export_additional_changes(additional_path, additional_changes)

    while True:
        try:
            print 'Uploading %s' % crawl.crawl_date.strftime('%Y-%m-%d')
            filename = '%s-%s-%s.csv'  % (account.member_id, spider.website_id, str(crawl.crawl_date))
            uploader.upload_file(path, os.path.join(config.SFTP_DST_NEW, filename))
            additional_filename = '%s-%s-%s.json-lines' % (account.member_id, spider.website_id, str(crawl.crawl_date))
            uploader.upload_file(additional_path, os.path.join(config.SFTP_DST_ADDITIONAL_NEW, additional_filename))
            break
        except:
            pass
import csv
import sys
import os
import tempfile

from sqlalchemy import desc, and_
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE,
                                             '../../productspidersweb')))

from productspidersweb.models import Spider, Crawl, Account
sys.path.append('..')

from db import Session
from uploader import Uploader, UploaderException, upload_changes
from export import export_changes_new
from productsupdater import ProductsUpdater
import config

DATA_DIR = os.path.abspath(os.path.join(HERE, '../../data'))

if len(sys.argv) < 2:
    print "Usage %s <website id>"
    sys.exit(1)


db_session = Session()
website_id = sys.argv[1]
spiders = db_session.query(Spider).filter(and_(Spider.website_id == website_id, Spider.enabled == True))
for spider in spiders:
    account = db_session.query(Account).get(spider.account_id)
    crawl = db_session.query(Crawl)\
                      .filter(and_(Crawl.spider_id == spider.id, Crawl.status == 'upload_finished'))\
                      .order_by(desc(Crawl.crawl_date)).first()

    if not crawl:
        continue

    updater = ProductsUpdater(db_session)
    uploader = Uploader()
    server_data = config.SERVERS['s2']
    uploader.set_host_data(server_data['host'], server_data['user'], server_data['password'], server_data['port'])
    old_products = []

    with open(os.path.join(DATA_DIR, '%s_products.csv' % crawl.id)) as f:
        reader = csv.DictReader(f)
        products = [row for row in reader]

    changes, additions, deletions, updates = updater.compute_changes(crawl.id, old_products, products,
                                                                     crawl.spider.silent_updates,
                                                                     set_crawl_data=False)

    path = os.path.join(tempfile.gettempdir(), '%s_changes.csv' % crawl.id)
    export_changes_new(path, changes, crawl.spider.website_id)

    while True:
        try:
            print 'Uploading %s %s' % (spider.name, crawl.crawl_date.strftime('%Y-%m-%d'))
            filename = '%s-%s-%s.csv'  % (account.member_id, spider.website_id, str(crawl.crawl_date))
            uploader.upload_file(path, os.path.join(config.SFTP_DST_NEW, filename))
            break
        except:
            pass


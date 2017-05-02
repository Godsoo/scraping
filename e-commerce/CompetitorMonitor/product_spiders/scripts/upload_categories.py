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

db_session = Session()

accounts = db_session.query(Account).all()

for i, account in enumerate(accounts):
    print i, '/', len(accounts), account.name
    account_id = account.id
    spiders = db_session.query(Spider).join(Account).filter(Account.id == account_id)
    for spider in spiders:
        try:
            account = db_session.query(Account).get(spider.account_id)
            crawl = db_session.query(Crawl)\
                              .filter(and_(Crawl.spider_id == spider.id, Crawl.status == 'upload_finished'))\
                              .order_by(desc(Crawl.crawl_date)).first()

            if not crawl:
                continue

            uploader = Uploader()
            server_data = config.SERVERS['s2']
            uploader.set_host_data(server_data['host'], server_data['user'], server_data['password'], server_data['port'])

            categories = set()
            with open(os.path.join(DATA_DIR, '%s_products.csv' % crawl.id)) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['category']:
                        categories.add(row['category'])

            with open('/tmp/categories.csv', 'w') as f:
                writer = csv.writer(f)
                for c in categories:
                    writer.writerow([c])
        except Exception:
            print 'Failed'
            continue

        while True:
            try:
                print 'Uploading %s %s' % (spider.name, crawl.crawl_date.strftime('%Y-%m-%d'))
                filename = '%s-%s.csv' % (account.member_id, spider.website_id)
                uploader.upload_file('/tmp/categories.csv', '/home/compmon/compmon2/scripts/db_migration/categories/'
                                                            + filename)
                break
            except:
                pass



import csv
import sys
import os
import tempfile
from datetime import date, datetime

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

if len(sys.argv) < 4:
    print "Usage %s <account id> <from date> <to date>"
    sys.exit(1)


def get_date(d):
    d = datetime.strptime(d, '%Y-%m-%d')
    return date(year=d.year, month=d.month, day=d.day)

db_session = Session()
website_id = sys.argv[1]
from_date = get_date(sys.argv[2])
to_date = get_date(sys.argv[3])

SF = '/home/compmon/compmon2/data_importers/changes_fix'

spiders = [db_session.query(Spider).filter(Spider.website_id == website_id).first()]
for spider in spiders:
    account = db_session.query(Account).get(spider.account_id)
    crawls = db_session.query(Crawl)\
                       .filter(and_(Crawl.spider_id == spider.id,
                                    Crawl.status == 'upload_finished',
                                    Crawl.crawl_date >= from_date,
                                    Crawl.crawl_date <= to_date))\
                       .order_by(desc(Crawl.crawl_date)).all()

    updater = ProductsUpdater(db_session)
    uploader = Uploader()
    server_data = config.SERVERS['s2']
    uploader.set_host_data(server_data['host'], server_data['user'], server_data['password'], server_data['port'])
    for crawl in crawls:
        previous_crawl = db_session.query(Crawl)\
                                   .filter(and_(Crawl.spider_id == crawl.spider_id,
                                                Crawl.id < crawl.id))\
                                           .order_by(desc(Crawl.crawl_date)).first()

        old_products = []
        if previous_crawl:
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

        while True:
            try:
                print 'Uploading %s %s' % (spider.name, crawl.crawl_date.strftime('%Y-%m-%d'))
                filename = '%s-%s-%s.csv'  % (account.member_id, spider.website_id, str(crawl.crawl_date))
                uploader.upload_file(path, os.path.join(SF, filename))
                break
            except:
                pass


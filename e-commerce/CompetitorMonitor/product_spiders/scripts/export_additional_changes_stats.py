import csv
import json
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
import config

DATA_DIR = os.path.abspath(os.path.join(HERE, '../../data'))

db_session = Session()

spiders = db_session.query(Spider).join(Account).filter(and_(Spider.enabled == True, Account.enabled == True)).all()

results = []
fields = ['name', 'url', 'shipping_cost', 'sku',
          'brand', 'category', 'image_url', 'stock', 'dealer']
for i, spider in enumerate(spiders):
    print 'processing spider %s of %s' % (i, len(spiders))
    crawl = db_session.query(Crawl)\
                      .filter(and_(Crawl.spider_id == spider.id, Crawl.status == 'upload_finished'))\
                      .order_by(desc(Crawl.crawl_date)).first()
    if crawl:
        with open(os.path.join(DATA_DIR, 'additional/%s_changes.json' % crawl.id)) as f:
            additional_changes = json.load(f)
            changes_count = {}
            for product in additional_changes:
                for field in product['changes']:
                    if field in fields:
                        changes_count[field] = changes_count.get(field, 0) + 1

            results.append([spider, changes_count, crawl.additional_changes_count])

results.sort(key=lambda e: e[2], reverse=True)

with open('out.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['Spider', 'Additional Changes'] + fields)
    for spider in results:
        writer.writerow([spider[0].name, str(spider[2])] + [str(spider[1].get(field, 0)) for field in fields])
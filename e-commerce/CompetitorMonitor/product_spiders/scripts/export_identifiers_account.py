import sys
import os
import csv

from sqlalchemy import desc, and_

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE,
                                             '../../productspidersweb')))

sys.path.append('..')

from productspidersweb.models import Spider, Crawl, Account

from db import Session

DATA_DIR = os.path.abspath(os.path.join(HERE, '../../data'))

if __name__ == '__main__':
    db_session = Session()
    if len(sys.argv) < 2:
        print "Usage %s <member id>" % sys.argv[0]
        sys.exit(1)

    member_id = sys.argv[1]

    spiders = db_session.query(Spider).join(Account).filter(Account.member_id == member_id).all()

    products = {}
    for spider in spiders:
        crawls = db_session.query(Crawl).filter(and_(Crawl.spider_id == spider.id, Crawl.status == 'upload_finished')).order_by(desc(Crawl.crawl_date)).all()
        for crawl in crawls:
            print 'Reading crawl', crawl.id, spider.name
            f = open(os.path.join(DATA_DIR, '%s_products.csv' % crawl.id))
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get('identifier'):
                    continue
                p = products.get('%s:%s' % (spider.website_id, row['identifier']))
                r = [row['identifier'], row['sku'], row['name'], row['url'], str(spider.website_id)]
                if not p:
                    products['%s:%s' % (spider.website_id, row['identifier'])] = [r]
                else:
                    if r not in p:
                        p.append(r)

            f.close()

    with open(os.path.join(HERE, '%s.csv' % member_id), 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['identifier', 'sku', 'name', 'url', 'website_id'])
        for k in products:
            row = products[k]
            for subrow in row:
                writer.writerow(subrow)



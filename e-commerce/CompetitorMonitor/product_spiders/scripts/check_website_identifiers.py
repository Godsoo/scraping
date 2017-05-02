import sys
import os
import csv

from sqlalchemy import desc, and_, or_

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE,
                                             '../../productspidersweb')))

sys.path.append('..')

from productspidersweb.models import Spider, Crawl

from db import Session

DATA_DIR = os.path.abspath(os.path.join(HERE, '../../data'))

if __name__ == '__main__':
    db_session = Session()
    if len(sys.argv) < 2:
        print "Usage %s <website id>" % sys.argv[0]
        sys.exit(1)

    website_id = sys.argv[1]
    spider = db_session.query(Spider).filter(Spider.website_id == website_id).first()

    last_crawl = db_session.query(Crawl).filter(and_(Crawl.spider_id == spider.id,
                                                     or_(Crawl.status == 'upload_finished',
                                                         Crawl.status == 'processing_finished')))\
                                        .order_by(desc(Crawl.crawl_date)).first()


    with open(os.path.join(DATA_DIR, '%s_products.csv' % last_crawl.id)) as f:
        reader = csv.DictReader(f)
        identifiers = []
        total_products = 0
        without_identifiers = 0
        non_unique_identifiers = []
        for row in reader:
            total_products += 1
            identifier = row['identifier']
            if not identifier:
                without_identifiers += 1
            else:
                if identifier in identifiers:
                    non_unique_identifiers.append(identifier)
                else:
                    identifiers.append(identifier)

        print 'Total products: %s' % total_products
        print 'Products without identifiers: %s' % without_identifiers
        if non_unique_identifiers:
            print 'Non unique identifiers: %s' % '|'.join(non_unique_identifiers)

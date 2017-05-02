import sys
import os
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE, '../../productspidersweb')))

from productspidersweb.models import DeletionsReview
sys.path.append('..')

from db import Session
import config


def deleted_products_review_purge(db_session):
    db_session.query(DeletionsReview).\
        filter(DeletionsReview.status == 'new').\
        filter(DeletionsReview.crawl_date < (datetime.date.today() - datetime.timedelta(config.deletions_review_purge_days-1))).\
        delete()
    db_session.commit()


if __name__ == '__main__':
    db_session = Session()
    deleted_products_review_purge(db_session)
    db_session.close()
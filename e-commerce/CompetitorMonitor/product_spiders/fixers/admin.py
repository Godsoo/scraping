import os
import shutil

from db import Session
from productspidersweb.models import (
    Crawl,
    Spider,
    Account,
)

from config import DATA_DIR, SERVERS
import pandas as pd

from datetime import datetime

import re
from difflib import SequenceMatcher

import time


class AdminTasks(object):

    @staticmethod
    def detect_duplicates(spider_id):
        duplicates = pd.DataFrame()

        db_session = Session()

        last_crawl = db_session.query(Crawl)\
            .filter(Crawl.spider_id == int(spider_id),
                    Crawl.status == 'errors_found')\
            .order_by(Crawl.id.desc(),
                      Crawl.crawl_date.desc())\
            .limit(1).first()

        if last_crawl:
            products_filename = os.path.join(DATA_DIR, '%s_products.csv' % last_crawl.id)

            df = pd.read_csv(products_filename, dtype=pd.np.str)
            field = 'identifier'
            duplicates = df[df.duplicated([field])]
            duplicates = duplicates.where(pd.notnull(duplicates), None)
            duplicates['crawl_date'] = last_crawl.crawl_date.strftime('%d/%m/%Y')

        db_session.close()

        return duplicates.to_dict('records')

    @staticmethod
    def remove_duplicates(spider_id):
        total_duplicate = 0
        db_session = Session()

        last_crawl = db_session.query(Crawl)\
            .filter(Crawl.spider_id == int(spider_id),
                    Crawl.status == 'errors_found')\
            .order_by(Crawl.id.desc(),
                      Crawl.crawl_date.desc())\
            .limit(1).first()

        if last_crawl:
            products_filename = os.path.join(DATA_DIR, '%s_products.csv' % last_crawl.id)

            df = pd.read_csv(products_filename, dtype=pd.np.str)
            field = 'identifier'
            duplicates = df[df.duplicated([field])]
            total_duplicate = getattr(duplicates[field], 'count')()

            if total_duplicate:
                backup_name = '%s.bak' % products_filename
                backup_i = 0
                while os.path.exists(os.path.join(DATA_DIR, backup_name)):
                    backup_i += 1
                    backup_name = '%s.bak.%s' % (products_filename, str(backup_i))
                shutil.copy(products_filename, os.path.join(DATA_DIR, backup_name))

                df = df.drop_duplicates('identifier', take_last=True)
                df.to_csv(products_filename, index=False)

        db_session.close()

        return total_duplicate

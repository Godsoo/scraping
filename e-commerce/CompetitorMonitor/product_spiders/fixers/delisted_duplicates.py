# -*- coding: utf-8 -*-

import os
import shutil

from db import Session
from productspidersweb.models import (
    DelistedDuplicateError,
    Crawl,
    Spider,
    Account,
)

from config import DATA_DIR
import pandas as pd


def error_log_decorator(callback):
    def new_callback(obj, *args, **kwargs):
        try:
            callback(obj, *args, **kwargs)
        except Exception, e:
            if hasattr(obj, 'set_with_error'):
                obj.set_with_error(str(e))
            raise e
    return new_callback


class DelistedDuplicateFixer(object):

    STARTED = 1
    ERROR = -1
    COMPLETED = 2
    REVERTED = 3

    def __init__(self, issue_id, task_uid):
        self._issue_id = issue_id
        self._task_uid = task_uid
        self.init_changes()

    def init_changes(self):
        db_session = Session()
        dd_error = db_session.query(DelistedDuplicateError).get(self._issue_id)
        if not dd_error:
            db_session.close()
            raise Exception('The issue with ID %s does not exist' % self._issue_id)

        self._filename = os.path.join(DATA_DIR, dd_error.filename)
        if not os.path.exists(self._filename):
            db_session.close()
            raise Exception('The filename %s does not exist' % dd_error.filename)
        self._crawl_id = dd_error.crawl_id
        self._website_id = dd_error.website_id
        issues_df = pd.read_csv(self._filename, dtype=pd.np.str)
        self._changes = pd.DataFrame()
        self._changes['identifier'] = issues_df['new_identifier']
        self._changes['old_identifier'] = issues_df['old_identifier']
        self._changes['website_id'] = dd_error.website_id
        self._changes['crawl_id'] = dd_error.crawl_id
        db_session.close()

    @error_log_decorator
    def fix_csv(self):
        print 'Fixing csv...'

        crawl_id = self._crawl_id
        products_filename = os.path.join(DATA_DIR, '%s_products.csv' % crawl_id)
        if os.path.exists(products_filename):
            # Makes products file backup
            backup_name = '%s.bak' % products_filename
            backup_i = 0
            while os.path.exists(os.path.join(DATA_DIR, backup_name)):
                backup_i += 1
                backup_name = '%s.bak.%s' % (products_filename, str(backup_i))
            shutil.copy(products_filename, os.path.join(DATA_DIR, backup_name))

            products_df = pd.read_csv(products_filename, dtype=pd.np.str)
            products_found = products_df[products_df['identifier'].isin(self._changes['identifier'])]
            products_not_found = products_df[products_df['identifier'].isin(self._changes['identifier']) == False]
            new_old_products = pd.DataFrame(columns=products_df.columns, dtype=pd.np.str)

            new_old_products = pd.merge(products_found, self._changes, on='identifier')
            new_old_products['identifier'] = new_old_products['old_identifier']
            del new_old_products['old_identifier']
            new_old_products = new_old_products.append(products_not_found)
            new_old_products = new_old_products.drop_duplicates('identifier', take_last=True)
            new_old_products.to_csv(products_filename, index=False, index_label=False, columns=products_df.columns, encoding='utf-8')
            self.generate_identifier_replacements_file()
        else:
            raise Exception('File with name %s does not exist' % products_filename)

    def generate_identifier_replacements_file(self):
        filename = os.path.join(DATA_DIR, '%s_identifier_replacements.csv' % self._website_id)
        if not os.path.exists(filename):
            self._changes = self._changes.drop_duplicates('old_identifier', take_last=True)
            self._changes.to_csv(filename, index=False, columns=['identifier', 'old_identifier'], encoding='utf-8')
        else:
            replacements = pd.read_csv(filename, dtype=pd.np.str)
            not_found = replacements[replacements['old_identifier'].isin(self._changes['old_identifier']) == False]
            new_changes = pd.DataFrame()
            new_changes['identifier'] = self._changes['identifier']
            new_changes['old_identifier'] = self._changes['old_identifier']
            new_changes = new_changes.append(not_found)
            new_changes.to_csv(filename, index=False, columns=['identifier', 'old_identifier'], encoding='utf-8')

    def _export_issues_to_csv(self):
        return [self._filename]

    def _get_system_name(self, website_id):
        system_name = 'new_system'

        db_session = Session()
        spider_db = db_session.query(Spider).filter(Spider.website_id == int(website_id)).first()
        account = db_session.query(Account).get(spider_db.account_id)
        if account.upload_destinations:
            system_name = account.upload_destinations[0].name
            if system_name != 'new_system':
                system_name = system_name.split('_')[0]
        db_session.close()

        return system_name

    @error_log_decorator
    def close(self, mark_fixed=True):
        db_session = Session()
        dd_error = db_session.query(DelistedDuplicateError).get(self._issue_id)
        dd_error.fixed = True
        db_session.add(dd_error)
        db_session.commit()
        db_session.close()

    @classmethod
    def detect_issues(cls, website_id, field_names, match_all=True, ignore_case=False):
        db_session = Session()

        issues_count = 0
        issues_detected = []

        spider_id = db_session.query(Spider)\
            .filter(Spider.website_id == int(website_id))\
            .first().id

        error_crawl = db_session.query(Crawl)\
            .filter(Crawl.spider_id == int(spider_id),
                    Crawl.status == 'errors_found')\
            .order_by(Crawl.crawl_date.desc(),
                      Crawl.id.desc())\
            .limit(1).first()

        if error_crawl:
            last_filename = os.path.join(DATA_DIR, '%s_products.csv' % error_crawl.id)
            prev_filename = os.path.join(DATA_DIR, '%s_all_products.csv' % website_id)
            if not os.path.exists(prev_filename):
                before_error_crawl = db_session.query(Crawl) \
                    .filter(Crawl.spider_id == int(spider_id),
                            Crawl.status != 'errors_found') \
                    .order_by(Crawl.crawl_date.desc(),
                              Crawl.id.desc()) \
                    .limit(1).first()
                if before_error_crawl:
                    prev_filename = os.path.join(DATA_DIR, '%s_products.csv' % before_error_crawl.id)

            if os.path.exists(last_filename) and os.path.exists(prev_filename):
                last_data = pd.read_csv(last_filename, dtype=pd.np.str)
                prev_data = pd.read_csv(prev_filename, dtype=pd.np.str)

                if ignore_case:
                    new_field_names = []
                    for field_name in field_names:
                        new_field_name = field_name + '_lower'
                        prev_data[new_field_name] = prev_data[field_name].str.lower()
                        last_data[new_field_name] = last_data[field_name].str.lower()
                        new_field_names.append(new_field_name)
                    field_names = new_field_names

                if match_all:
                    matched_products = pd.merge(prev_data, last_data, on=field_names, suffixes=('_old', '_new'))
                else:
                    for field_name in field_names:
                        matched_products = pd.merge(prev_data, last_data, on=field_name, suffixes=('_old', '_new'))
                        if not matched_products.empty:
                            break

                for i, row in matched_products.iterrows():

                    if row['identifier_old'] == row['identifier_new']:
                        continue

                    new_row = {
                        'name': row['name_old'] if 'name_old' in row else row['name'],
                        'old_identifier': row['identifier_old'],
                        'old_url': row['url_old'] if 'url_old' in row else row['url'],
                        'new_identifier': row['identifier_new'],
                        'new_url': row['url_new'] if 'url_new' in row else row['url'],
                    }
                    issues_detected.append(new_row)
                    issues_count += 1

        db_session.close()

        if error_crawl and issues_count and issues_detected:
            filename = '%s_%s_delisted_duplicate_errors.csv' % (website_id, error_crawl.id)
            filename_full = os.path.join(DATA_DIR, filename)
            issues_detected_df = pd.DataFrame(issues_detected, dtype=pd.np.str)
            try:
                issues_detected_df.to_csv(filename_full, index=False, encoding='utf-8')
            except:
                issues_detected_df.to_csv(filename_full, index=False)

            db_session = Session()
            dd_error = db_session.query(DelistedDuplicateError)\
                .filter(DelistedDuplicateError.website_id == website_id,
                        DelistedDuplicateError.crawl_id == error_crawl.id)\
                .first()
            if not dd_error:
                dd_error = DelistedDuplicateError()
            dd_error.website_id = website_id
            dd_error.crawl_id = error_crawl.id
            dd_error.filename = filename
            dd_error.fixed = False
            db_session.add(dd_error)
            db_session.commit()
            db_session.close()

        return issues_count

    @classmethod
    def import_issues(cls, website_id, filename):
        db_session = Session()

        spider_id = db_session.query(Spider)\
            .filter(Spider.website_id == int(website_id))\
            .first().id

        error_crawl = db_session.query(Crawl)\
            .filter(Crawl.spider_id == int(spider_id),
                    Crawl.status == 'errors_found')\
            .order_by(Crawl.crawl_date.desc(),
                      Crawl.id.desc())\
            .limit(1).first()

        if error_crawl:
            new_filename = '%s_%s_delisted_duplicate_errors.csv' % (website_id, error_crawl.id)
            new_filename_full = os.path.join(DATA_DIR, new_filename)
            new_filename_full_tmp = new_filename_full + '~'
            shutil.copy(filename, new_filename_full_tmp)

            os.rename(new_filename_full_tmp, new_filename_full)

            dd_error = db_session.query(DelistedDuplicateError)\
                .filter(DelistedDuplicateError.website_id == website_id,
                        DelistedDuplicateError.crawl_id == error_crawl.id)\
                .first()
            if not dd_error:
                dd_error = DelistedDuplicateError()
            dd_error.website_id = website_id
            dd_error.crawl_id = error_crawl.id
            dd_error.filename = new_filename
            dd_error.fixed = False
            db_session.add(dd_error)
            db_session.commit()

        db_session.close()

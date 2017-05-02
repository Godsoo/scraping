# -*- coding: utf-8 -*-

import os
import requests
import pandas as pd
from product_spiders.db import Session
from productspidersweb.models import (
    Crawl,
    DelistedDuplicateError,
)
from datetime import datetime
from product_spiders.utils import remove_punctuation
from product_spiders.config import (
    DATA_DIR,
    new_system_api_roots as API_ROOTS,
)

from scrapy import log


class DelistedDuplicatesDetection(object):

    meaning_fields = ['name', 'category', 'brand', 'dealer', 'sku', 'url']
    possible_identifier_like_fields = {'sku'}
    possible_identifier_containers = {'url'}

    def __init__(self, current_crawl):
        self.current_crawl = current_crawl
        self.all_products_df = pd.DataFrame()
        self.init_all_products_hashes()
        self.errors = []

    def init_all_products_hashes(self):
        db_session = Session()
        spider_db = self.current_crawl.spider
        try:
            upload_dst = spider_db.account.upload_destinations[0].name
        except (TypeError, IndexError):
            upload_dst = 'new_system'
        all_products_filename = os.path.join(DATA_DIR, '%s_all_products.csv' % spider_db.website_id)
        if os.path.exists(all_products_filename):
            self.all_products_df = pd.read_csv(all_products_filename, dtype=pd.np.str)
            if not self.all_products_df.empty:
                last_date = self.all_products_df.iloc[0]['last_date']
                new_products = pd.DataFrame(self.get_all_products_website(upload_dst, spider_db.website_id, last_date))
                if not new_products.empty:
                    self.all_products_df.append(new_products)
        if not os.path.exists(all_products_filename) or self.all_products_df.empty:
            log.msg('DELISTED DUPLICATES DETECTION: %s does not exists' % all_products_filename)
            self.all_products_df = pd.DataFrame(self.get_all_products_website(upload_dst, spider_db.website_id))

        if not self.all_products_df.empty:
            # Check data integrity
            total_products = self.get_all_products_count(upload_dst, spider_db.website_id)
            total_collected = self.all_products_df.identifier.count()
            if total_products != total_collected:
                # Try get all products
                log.msg('DELISTED DUPLICATES DETECTION: total products count is different to number of products collected (%s / %s)' %
                        (total_products, total_collected))
                log.msg('DELISTED DUPLICATES DETECTION: trying getting all products')
                self.all_products_df = pd.DataFrame(self.get_all_products_website(upload_dst, spider_db.website_id))
            last_crawl = db_session.query(Crawl)\
                .filter(Crawl.spider_id == spider_db.id,
                        Crawl.status == 'upload_finished')\
                .order_by(Crawl.crawl_date.desc(),
                          Crawl.id.desc()).limit(1).first()
            if last_crawl:
                self.all_products_df['last_date'] = str(last_crawl.crawl_date)
            else:
                self.all_products_df['last_date'] = str(datetime.now().date())
            try:
                self.all_products_df.to_csv(all_products_filename, index=False, encoding='utf-8')
            except:
                self.all_products_df.to_csv(all_products_filename, index=False)

            self.all_products_df = self.all_products_df.where(pd.notnull(self.all_products_df), None)
            self.gen_hashes()

        db_session.close()

    def gen_hashes(self):
        if not self.all_products_df.empty:
            fields = self.get_fields_configuration_for_hash(dict(self.all_products_df.iloc[0]))
            for i, f in enumerate(fields):
                if i < 1:
                    self.all_products_df['hash'] = self.all_products_df[f].apply(remove_punctuation)
                else:
                    self.all_products_df['hash'] += ':' + self.all_products_df[f].apply(remove_punctuation)

    def detect_delisted_duplicates(self, additions):
        if not self.all_products_df.empty:
            crawl_filename = os.path.join(DATA_DIR, '%s_products.csv' % self.current_crawl.id)
            try:
                crawl_identifiers = pd.read_csv(crawl_filename, usecols=['identifier'], encoding='utf-8', dtype=pd.np.str)['identifier'].tolist()
            except:
                crawl_identifiers = []
            for new_product in additions:
                product_hash = self.get_hash_product(new_product)
                product_found = self.all_products_df[self.all_products_df['identifier'] != new_product['identifier']]
                if not product_found.empty:
                    product_found = product_found[product_found['hash'] == product_hash]
                    all_product_found_hash = self.all_products_df[self.all_products_df['hash'] == product_hash]
                    # Exclude duplicates
                    if not product_found.empty and all_product_found_hash['hash'].count() == 1:
                        old_product = dict(product_found.iloc[0])
                        if old_product['identifier'] not in crawl_identifiers:
                            error_found = {
                                'name': (new_product.get('name') or '').decode('utf-8'),
                                'old_identifier': old_product['identifier'].decode('utf-8'),
                                'old_url': (old_product.get('url') or '').decode('utf-8'),
                                'new_identifier': new_product['identifier'].decode('utf-8'),
                                'new_url': (new_product.get('url') or '').decode('utf-8'),
                            }

                            self.errors.append(error_found)
        return len(self.errors)

    def export_delisted_duplicate_errors(self):
        website_id = self.current_crawl.spider.website_id
        crawl_id = self.current_crawl.id
        filename = '%s_%s_delisted_duplicate_errors.csv' % (website_id, crawl_id)
        filename_full = os.path.join(DATA_DIR, filename)
        errors_df = pd.DataFrame(self.errors, dtype=pd.np.str)
        try:
            errors_df.to_csv(filename_full, index=False, encoding='utf-8')
        except:
            errors_df.to_csv(filename_full, index=False)

        db_session = Session()
        dd_error = db_session.query(DelistedDuplicateError)\
            .filter(DelistedDuplicateError.website_id == website_id,
                    DelistedDuplicateError.crawl_id == crawl_id)\
            .first()
        if not dd_error:
            dd_error = DelistedDuplicateError()
        dd_error.website_id = website_id
        dd_error.crawl_id = crawl_id
        dd_error.filename = filename
        db_session.add(dd_error)
        db_session.commit()
        db_session.close()

    @classmethod
    def get_all_products_website(cls, upload_dst, website_id, last_date=''):
        products = []

        log.msg('DELISTED DUPLICATES DETECTION: Upload destination => %s' % upload_dst)
        if upload_dst in API_ROOTS:
            api_host = API_ROOTS[upload_dst]
            log.msg('DELISTED DUPLICATES DETECTION: api host => %s' % api_host)
        else:
            return products

        offset = 0
        limit = 1000
        next_page = True
        while next_page:
            t_number = 0
            retry_query = True
            if not last_date:
                url = '%s/api/get_all_products_website.json?website_id=%s&offset=%s&limit=%s&api_key=3Df7mNg' % \
                      (api_host, website_id, offset, limit)
            else:
                url = '%s/api/get_all_products_website.json?website_id=%s&offset=%s&limit=%s&gt_date=%s&api_key=3Df7mNg' % \
                      (api_host, website_id, offset, limit, last_date)
            products_found = []
            while retry_query and t_number < 10:
                t_number += 1
                try:
                    log.msg('DELISTED DUPLICATES DETECTION: get products => %s' % url)
                    r = requests.get(url, timeout=300)
                    products_found = r.json()['products']
                except:
                    pass
                else:
                    retry_query = False

            if not products_found:
                next_page = False
            else:
                products += products_found
                offset += limit

        return products

    @classmethod
    def get_all_products_count(cls, upload_dst, website_id):
        total = 0

        log.msg('DELISTED DUPLICATES DETECTION: Upload destination => %s' % upload_dst)
        if upload_dst in API_ROOTS:
            api_host = API_ROOTS[upload_dst]
            log.msg('DELISTED DUPLICATES DETECTION: api host => %s' % api_host)
        else:
            return total

        t_number = 0
        retry_query = True
        url = '%s/api/get_products_total_website.json?website_id=%s&api_key=3Df7mNg' % \
              (api_host, website_id)

        while retry_query and t_number < 10:
            t_number += 1
            try:
                log.msg('DELISTED DUPLICATES DETECTION: get products count => %s' % url)
                r = requests.get(url, timeout=300)
                total = r.json()['total']
            except:
                pass
            else:
                retry_query = False

        return total

    @classmethod
    def get_hash_product(cls, product):
        fields = cls.get_fields_configuration_for_hash(dict(product))
        return ':'.join([remove_punctuation(product[f]) for f in fields])

    @classmethod
    def get_fields_configuration_for_hash(cls, product):
        config = []
        for field in cls.meaning_fields:
            if field in cls.possible_identifier_like_fields:
                if product[field] is not None and product[field].lower() == product['identifier'].lower():
                    continue
            if field in cls.possible_identifier_containers:
                if product[field] is not None and product['identifier'].lower() in product[field].lower():
                    continue
            config.append(field)
        return config

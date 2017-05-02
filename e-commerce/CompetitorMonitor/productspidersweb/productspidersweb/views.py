import os
import shutil
import sys
import csv
import logging
import json
import urllib2
import urllib
import uuid
from datetime import (
    datetime,
    date,
    timedelta
)
from decimal import Decimal
from tempfile import TemporaryFile
from urlparse import urljoin

import requests
from requests.auth import HTTPBasicAuth

from math import ceil
from tempfile import NamedTemporaryFile

import transaction
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPNotFound, HTTPBadRequest
from pyramid.response import Response, FileResponse

from pyramid.security import (
    remember,
    forget,
    has_permission,

    Everyone,
    Authenticated
)

from pyramid_simpleform import Form
from pyramid_simpleform.renderers import FormRenderer

from sqlalchemy import and_, or_, desc, func
from sqlalchemy import Integer
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import cast
from sqlalchemy.sql import text
from sqlalchemy.ext.declarative import DeclarativeMeta

from productspidersweb.security import (
    authenticate,
    is_login_disabled,
)

from productspidersweb.models import (
    DBSession,
    DBSessionSimple,

    Account,
    Spider,
    SpiderDefault,
    NotificationReceiver,
    Crawl,
    CrawlHistory,
    SpiderError,
    UploadDestination, ProxyList,
    DeletionsReview,
    WorkerServer,
    DailyErrors,
    Note,
    AdditionalFieldsGroup,
    CrawlMethod,
    ScrapelySpiderData,
    ScrapelySpiderExtractor,
    UserLog,
    User,
    Group,
    UserGroup,
    Developer,
    SpiderException,
    SpiderErrorGroup,
    DelistedDuplicateError,
    SpiderUpload,

    ERROR_TYPES,
)
from productspidersweb.utils import (
    get_accounts,
    get_account,
    get_spider_source_file,
    get_sqlalchemy_json_encoder,
    DatetimeJSONEncoder,
    SPIDER_ERROR_STATUSES,
    TEMP_SPIDER_PATH,
    save_uploaded_file,
    validate_spider,
    clear_temp_spider,
    account_exists,
    create_spider_file,
    valid_spider_name,
    delete_spider,
    get_spider_class,
)
from productspidersweb.formschemas import (
    AccountSchema,
    SpiderSchema,
    AssemblaTicketSchema,
    ProxyListSchema,
    WorkerServerSchema,
    AdditionalFieldsGroupSchema
)

import productspidersweb.assembla as assembla

from utils import (
    get_logs_url,
    get_log_crawl,
    UI_CRAWL_STATUSES
)

TIMEZONES = ['GMT', 'America/Los_Angeles', 'America/New_York', 'Australia/Melbourne', 'Australia/Sydney',
             'Europe/Amsterdam', 'Europe/Berlin', 'Europe/Dublin',
             'Europe/Lisbon', 'Europe/London', 'Europe/Moscow', 'Europe/Paris', 'Europe/Stockholm']

HERE = os.path.dirname(__file__)
path = os.path.abspath(os.path.join(HERE, '../..'))

DATA_DIR = os.path.join(path, 'data')

sys.path.append(path)
path = os.path.join(path, 'product_spiders')

sys.path.append(path)

from uploader import Uploader, upload_changes, upload_crawl_changes, UploaderException
from export import (export_changes_new,
                    export_metadata, export_metadata_changes, export_additional_changes)
from productsupdater import ProductsUpdater
from productsupdater.metadataupdater import MetadataUpdater
from metadata_db import MetadataDB

from scripts import upload_crawls
from scheduler import schedule_spiders

from custom_crawl_methods import CRAWL_METHODS, CRAWL_METHOD_PARAMS, CRAWL_METHOD_FIT_CHECK_FUNCS

from config import (
    PROXY_SERVICE_HOST,
    PROXY_SERVICE_USER,
    PROXY_SERVICE_PSWD,
    PROXY_SERVICE_ALGORITHM_CHOICES,
)

from product_spiders.utils import get_crawl_meta_file, get_crawl_meta_changes_file, \
    read_json_lines_from_file, get_crawl_additional_changes_file, read_json_lines_from_file_generator

from security import get_user


ERROR_TYPES_DICT = dict(ERROR_TYPES)

from tasks.fixer import (
    fix_delisted_duplicates,
    detect_duplicates,
    import_delisted_duplicates_issues,
    admin_remove_duplicates_task,
    admin_detect_duplicates_task,
)

from product_spiders.downloadermiddleware import cache_storages
from product_spiders.utils import is_cron_today
from product_spiders.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM
from product_spiders.emailnotifier import EmailNotifier
account_status_change_receivers = [
    'stephen.sharp@competitormonitor.com',
    'steven.seaward@competitormonitor.com',
    'yuri.abzyanov@competitormonitor.com'
]

from spider_ratings import (
    get_metrics_schema, process_ratings_form, save_spider_rating, get_spider_rating_params)


class Menu(object):

    def __init__(self):
        self.menu = {
            'overview': {
                'name': 'Overview',
                'active': True,
                'route': 'dashboard',
                'order': 1,
                'primary': True,
                'submenu': [],
            },
            'crawlers': {
                'name': 'Crawlers',
                'active': False,
                'route': 'list_accounts',
                'order': 2,
                'primary': True,
                'submenu': [],
            },
            'maintenance': {
                'name': 'Maintenance',
                'active': False,
                'route': None,
                'order': 3,
                'primary': True,
                'submenu': [
                    {'name': 'Delisted Duplicates',
                     'active': False,
                     'route': 'delisted_duplicates'},
                    {'name': 'Remove Duplicates',
                     'active': False,
                     'route': 'remove_duplicates'},
                    {'name': 'Spiders for upload',
                     'active': False,
                     'route': 'spiders_upload'}]
            },
            'admin': {
                'name': 'Admin',
                'active': False,
                'route': 'admin',
                'order': 4,
                'primary': True,
                'submenu': [],
            },
        }

    def get_iterable(self):
        values = self.menu.values()
        return sorted(values, key=lambda m: m['order'])

    def set_active(self, k):
        if k in self.menu:
            for m_k, m_v in self.menu.items():
                if m_k == k:
                    self.menu[m_k]['active'] = True
                else:
                    self.menu[m_k]['active'] = False

STATUSES_LABELS = {'running': 'Crawl started',
                   'crawl_finished': 'Crawl finished',
                   'schedule_errors': 'Scheduling errors',
                   'errors_found': 'Errors found',
                   'processing_finished': 'Processing of changes finished',
                   'upload_finished': 'Upload to CM done',
                   'upload_errors': 'Upload to CM errors',
                   'retry': 'Spider retry'}

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
DAYS_DATA = []
for i, day in enumerate(DAYS):
    d = {'value': i, 'text': day}
    DAYS_DATA.append(d)

log = logging.getLogger(__name__)

def _merge_response_headers(headers, response):
    return headers + [(k, v) for k, v in response.headers.items() if k == 'Set-Cookie']

def _count_real_errors():
    db_session = DBSession()

    count_spiders = db_session.query(Spider)\
        .join(SpiderError).filter(SpiderError.status == 'real').count()

    return count_spiders

def _count_possible_errors():
    db_session = DBSession()

    spiders1 = db_session.query(Spider).join(Crawl)\
        .filter(or_(Crawl.status == 'errors_found',
                    Crawl.status == 'upload_errors'))

    spiders2 = db_session.query(Spider).join(SpiderError)\
        .filter(SpiderError.status == 'possible')

    spiders = [spider for spider in spiders1.union(spiders2).all()
               if spider.error is None or (spider.error is not None and
                                           spider.error.status != 'real')]

    return len(spiders)

def _get_spiders_errors():
    db_session = DBSession()

    spiders_errors = db_session.query(SpiderError)\
        .filter(SpiderError.status == 'real').all()

    return spiders_errors

def _get_all_spiders(with_errors, count=None):
    db_session = DBSession()

    if with_errors == 'possible':
        spiders1 = db_session.query(Spider)\
            .join(Crawl).filter(or_(Crawl.status == 'errors_found', Crawl.status == 'upload_errors', Crawl.status == 'schedule_errors'))

        spiders2 = db_session.query(Spider)\
            .join(SpiderError).filter(SpiderError.status == 'possible')

        all_spiders = spiders1.union(spiders2)\
            .options(joinedload('account'))\
            .options(joinedload('error'))\
            .order_by(desc(Spider.priority_possible_errors))
        all_spiders = all_spiders.all()

        spiders = [spider for spider in all_spiders if spider.error is None or (spider.error is not None and spider.error.status != 'real')]

        if count:
            spiders = spiders[:int(count)]

        for spider in spiders:
            last_crawl = db_session.query(Crawl)\
                .filter(Crawl.spider_id == spider.id)\
                .order_by(Crawl.crawl_date.desc(),
                          desc(Crawl.id)).limit(1).first()
            if last_crawl:
                spider.last_crawl_run_count = db_session.query(func.count(CrawlHistory.id))\
                    .filter(CrawlHistory.crawl_id == last_crawl.id).scalar()
                if not spider.last_crawl_run_count > 0:
                    crawl_history = CrawlHistory(last_crawl)
                    db_session.add(crawl_history)
                    spider.last_crawl_run_count = 1
            else:
                spider.last_crawl_run_count = 0

    elif with_errors == 'real':
        error_types = ERROR_TYPES_DICT
        spiders = db_session.query(Spider)\
            .join(SpiderError).filter(SpiderError.status == 'real')\
            .options(joinedload('account'))\
            .options(joinedload('error'))
        spiders = spiders.all()
        if count:
            spiders = spiders[:int(count)]
        for spider in spiders:
            spider.assigned_to = spider.error.assigned_to_id
            if spider.assigned_to:
                developer = db_session.query(Developer).get(spider.assigned_to)
                spider.assigned_to_name = developer.name
            else:
                spider.assigned_to_name = ''
            spider.assembla_ticket_id = spider.error.assembla_ticket_id
            spider.starred = spider.error.starred
            if spider.error.error_desc:
                spider.error_type = spider.error.error_desc
            else:
                spider.error_type = error_types[spider.error.error_type]
            spider.error_type_value = spider.error.error_type

            last_crawl = db_session.query(Crawl)\
                .filter(Crawl.spider_id == spider.id)\
                .order_by(Crawl.crawl_date.desc(),
                          desc(Crawl.id)).limit(1).first()
            if last_crawl:
                spider.last_crawl_run_count = db_session.query(func.count(CrawlHistory.id))\
                    .filter(CrawlHistory.crawl_id == last_crawl.id).scalar()
                if not spider.last_crawl_run_count > 0:
                    crawl_history = CrawlHistory(last_crawl)
                    db_session.add(crawl_history)
                    spider.last_crawl_run_count = 1
            else:
                spider.last_crawl_run_count = 0

    elif not with_errors:
        spiders_in_db = db_session.query(Spider)
        spiders_in_db = spiders_in_db.all()
        spiders_in_db_names = [spider.name for spider in spiders_in_db]
        accounts = get_accounts()
        spider_names = []
        for acc, acc_spiders in accounts:
            spider_names += [spider_name for spider_name in acc_spiders if spider_name not in spiders_in_db_names]
        spiders = spiders_in_db
        for spider_name in spider_names:
            spider = db_session.query(Spider)\
            .filter(Spider.name == spider_name)\
            .options(joinedload('account'))\
            .first()
            if not spider:
                spider = Spider()
                spider.name = spider_name

            spiders.append(spider)
        if count:
            spiders = spiders[:int(count)]
    else:
        spiders = []
    return spiders

def _get_account_spiders(account_name, with_errors):
    db_session = DBSession()

    db_account = db_session.query(Account).filter(Account.name == account_name).first()

    if with_errors == 'possible':
        spiders1 = db_session.query(Spider).filter(Spider.error == None)\
            .filter(Spider.account_id == db_account.id)\
            .join(Crawl)\
            .filter(or_(Crawl.status == 'errors_found', Crawl.status == 'upload_errors', Crawl.status == 'schedule_errors'))

        spiders2 = db_session.query(Spider)\
            .filter(Spider.account_id == db_account.id)\
            .join(SpiderError)\
            .filter(SpiderError.status == 'possible')

        spiders = spiders1.union(spiders2)\
            .options(joinedload('account'))\
            .options(joinedload('error'))\
            .all()

    elif with_errors == 'real':
        spiders = db_session.query(Spider)\
            .filter(Spider.account_id == db_account.id)\
            .join(SpiderError)\
            .filter(SpiderError.status == 'real')\
            .options(joinedload('account'))\
            .options(joinedload('error'))\
            .all()
        for spider in spiders:
            spider.assigned_to = spider.error.assigned_to_id
            spider.assembla_ticket_id = spider.error.assembla_ticket_id

    elif not with_errors:
        if db_account:
            spiders = db_session.query(Spider)\
                .filter(Spider.account_id == db_account.id)\
                .options(joinedload('account'))\
                .options(joinedload('error'))\
                .all()
            db_spiders = [spider.name for spider in spiders]
        else:
            spiders = []
            db_spiders = []
        acc, acc_spiders = get_account(account_name)
        spider_names = [spider_name for spider_name in acc_spiders if spider_name not in db_spiders]

        for spider_name in spider_names:
            spider = db_session.query(Spider)\
                .filter(Spider.name == spider_name)\
                .options(joinedload('account'))\
                .first()
            if not spider:
                spider = Spider()
                spider.name = spider_name
            spiders.append(spider)
    else:
        spiders = []
    return spiders


def check_has_specific_errors(crawl_id, error_codes):
    db_session = DBSession()
    codes_to_check = set(error_codes)
    res = {code: False for code in error_codes}
    try:
        f = open(os.path.join(DATA_DIR, '%s_errors.csv' % crawl_id))
        products_updater = ProductsUpdater(db_session)
        for error in products_updater.get_errors(f):
            if not codes_to_check:
                break
            if int(error['code']) in codes_to_check:
                res[int(error['code'])] = True
    except IOError:
        pass
    return res


def _get_spiders_list(with_errors, request, count=None, account=None):
    if account is None:
        spiders = _get_all_spiders(with_errors, count=count)
    else:
        spiders = _get_account_spiders(account, with_errors)

    db_session = DBSession()
    for spider in spiders:
        spider.priority_possible_errors = 1 if spider.priority_possible_errors else 0
        if spider.account:
            spider.account_name = spider.account.name
            spider.account_enabled = spider.account.enabled
            spider.doc_url = request.route_url('show_doc', account=spider.account.name, spider=spider.name,
                                               _query={'ignore_referrer': True})
        else:
            spider.account_name = None
            spider.account_enabled = None
            spider.config_url = None
        if spider.account or account:
            account_name = spider.account.name if spider.account else account
            spider.config_url = request.route_url('config_spider', account=account_name, spider=spider.name)

        notes = db_session.query(Note).filter(Note.spider_id == spider.id).count()
        spider.notes_count = notes
        last_crawl = db_session.query(Crawl).filter(Crawl.spider_id == spider.id).order_by(Crawl.crawl_date.desc(), desc(Crawl.id)).limit(1).first()

        if with_errors and with_errors == 'real':
            spider.delisted_duplicates_errors = db_session.query(func.count(DelistedDuplicateError.id))\
                .filter(DelistedDuplicateError.fixed != True,
                        DelistedDuplicateError.website_id == spider.website_id)\
                .scalar()
        else:
            spider.delisted_duplicates_errors = 0
        if last_crawl:
            spider.crawl_id = last_crawl.id
            spider.crawl_status = last_crawl.status
            spider.crawl_date = last_crawl.crawl_date
            spider.products_count = last_crawl.products_count

            # error codes:
            # 18 - identifier change
            # 22 - delisted matches
            specific_errors = check_has_specific_errors(spider.crawl_id, [18, 22])
            spider.identifier_changes = specific_errors[18]
            spider.matches_delisted = specific_errors[22]
            spider.running_stats_url = ''
            if spider.crawl_status == 'running':
                spider.running_stats_url = request.route_url('get_running_crawl_stats') + '?crawl_id={}'.format(spider.crawl_id)
            if spider.crawl_status in ('errors_found', 'schedule_errors'):
                spider.set_valid_url = request.route_url('set_crawl_valid', crawl_id=spider.crawl_id)
                spider.delete_crawl_url = request.route_url('delete_crawl', crawl_id=spider.crawl_id)
                spider.errors_url = request.route_url('show_errors', crawl_id=spider.crawl_id)
            if spider.crawl_status == 'processing_finished':
                spider.upload_url = request.route_url('upload_changes', spider_id=spider.id, real_upload=1)
                spider.set_uploaded_url = request.route_url('upload_changes', spider_id=spider.id, real_upload=0)
            if spider.crawl_status == 'upload_errors':
                spider.reupload_url = request.route_url('upload_changes', spider_id=spider.id, real_upload=1)

            spider.crawls_url = request.route_url('list_crawls', spider_id=spider.id, _query={'reverse': '1'})
            spider.logs_url = get_logs_url(request, spider, DBSession())
        else:
            spider.crawl_id = None
            spider.crawl_status = None
            spider.crawl_date = None
            spider.products_count = None

            spider.crawl_status = None
            spider.crawl_date = None

            spider.identifier_changes = None
            spider.matches_delisted = None

        spider.change_error_status_url = request.route_url('change_spider_error_status')
        spider.save_error_assignment_url = request.route_url('save_spider_error_assignment')

        spider.assembla_authorization_url = request.route_url('assembla_authorization', _query={'spider_name': spider.name})
        spider.assembla_ticket_url = request.route_url('assembla_ticket_get', _query={'id': spider.id})

        spider.upload_spider_source = request.route_url('upload_spider_source', spider_id=spider.id)

    return spiders

def _get_additional_changes(path, file_format="json", start=0, end=None):
    res = []
    if file_format == 'json':
        with open(path) as f:
            products = json.load(f)
            for i, row in enumerate(products):
                if start <= i < end:
                    res.append(row)
                if end and i > end:
                    break
    elif file_format == 'json-lines':
        for i, row in enumerate(read_json_lines_from_file_generator(path)):
            if i < start:
                continue
            if end and i > end:
                break
            res.append(row)
    else:
        raise ValueError("Unknown file format for additional changes: %s" % file_format)
    return res

def _get_metadata_simple(path, file_format="json"):
    if file_format == 'json':
        with open(path) as f:
            data = json.load(f)
    elif file_format == 'json-lines':
        data = read_json_lines_from_file(path)
    else:
        raise ValueError("Unknown file format for meta: %s" % file_format)

    return data

'''
def _get_products_metadata(path, file_format="json"):
    try:
        data = _get_metadata_simple(path, file_format)

        products = []
        for product in data:
            product['price'] = Decimal(product['price'] if product.get('price') and product['price'] != 'None' else 0)
            product['identifier'] = product.get('identifier', '')
            product['sku'] = product.get('sku', '')
            products.append(product)

        return products
    except IOError:
        return []
'''

def _get_products_metadata(path, file_type="json", metadata_db=None, crawl_id=None):
    try:
        if file_type == "json":
            with open(path) as f:
                data = json.load(f)
                products = []
                for product in data:
                    product['price'] = Decimal(product['price'] if product.get('price')
                                               and product['price'] != 'None' else 0)
                    product['identifier'] = product.get('identifier', '')
                    product['sku'] = product.get('sku', '')
                    products.append(product)

                return products
        elif file_type == "json-lines":
            products = []
            from product_spiders.utils import read_json_lines_from_file_generator
            for i, product in enumerate(read_json_lines_from_file_generator(path)):
                product['price'] = Decimal(product['price'] if product.get('price')
                                               and product['price'] != 'None' else 0)
                product['identifier'] = product.get('identifier', '')
                product['sku'] = product.get('sku', '')
                if metadata_db:
                    metadata_db.set_metadata(product['identifier'], crawl_id, product['metadata'], insert=True)
                    product['metadata'] = None

                if i % 1000:
                    metadata_db.db_session.flush()
                products.append(product)

            metadata_db.db_session.flush()
            return products
        else:
            raise ValueError("Unknown metadata file format: %s" % file_type)
    except IOError:
        return []

def _get_changes(request, change_type=None):
    db_session = DBSession()
    crawl_id = request.matchdict['crawl_id']
    crawl = db_session.query(Crawl).get(crawl_id)

    if not crawl:
        return HTTPFound('/productspiders')

    products_updater = ProductsUpdater(db_session)
    try:
        f = open(os.path.join(DATA_DIR, '%s_changes_new.csv' % crawl.id))
    except IOError:
        f = open(os.path.join(DATA_DIR, '%s_changes_old.csv' % crawl.id))

    changes = products_updater.get_changes(f)
    if change_type is not None:
        if type(change_type) is tuple:
            changes = filter(lambda x: x['change_type'] in change_type, changes)
        else:
            changes = filter(lambda x: x['change_type'] == change_type, changes)
    return dict(crawl=crawl, changes=changes)

def _get_changes_paged(request, change_type=None):
    db_session = DBSession()
    crawl_id = request.matchdict['crawl_id']
    crawl = db_session.query(Crawl).get(crawl_id)

    if not crawl:
        return HTTPFound('/productspiders')

    per_page = 100

    page = int(request.GET.get('page', 1))
    start = (page - 1) * per_page

    end = start + per_page

    if not change_type:
        pages_count = (crawl.changes_count / per_page) + 1
    elif change_type == 'deletion':
        pages_count = (crawl.deletions_count / per_page) + 1
    elif change_type == 'addition':
        pages_count = (crawl.additions_count / per_page) + 1
    elif 'update' in change_type:
        pages_count = (crawl.updates_count / per_page) + 1
    else:
        pages_count = 0

    products_updater = ProductsUpdater(db_session)
    try:
        f = open(os.path.join(DATA_DIR, '%s_changes_new.csv' % crawl.id))
    except IOError:
        f = open(os.path.join(DATA_DIR, '%s_changes_old.csv' % crawl.id))

    changes = products_updater.get_changes(f)
    if change_type is not None:
        if type(change_type) is tuple:
            changes = filter(lambda x: x['change_type'] in change_type, changes)
        else:
            changes = filter(lambda x: x['change_type'] == change_type, changes)

    res = []
    for i, change in enumerate(changes):
        if start <= i < end:
            res.append(change)
        if i > end:
            break
    return dict(crawl=crawl, changes=res, page=page, pages_count=pages_count)

def _get_errors(crawl_id):
    db_session = DBSession()

    errors = []
    crawl = db_session.query(Crawl).get(crawl_id)

    if crawl:

        if crawl.error_message:
            for msg in crawl.error_message.split("\n"):
                errors.append({'message': msg})

        products_updater = ProductsUpdater(db_session)
        try:
            f = open(os.path.join(DATA_DIR, '%s_errors.csv' % crawl.id))
            errors += products_updater.get_errors(f)
        except IOError:
            pass

    return errors

def has_duplicate_identifiers(crawl_id):
    if not os.path.exists(os.path.join(DATA_DIR, '%s_errors.csv' % crawl_id)):
        return False
    try:
        f = open(os.path.join(DATA_DIR, '%s_errors.csv' % crawl_id))
        for line in f:
            if 'duplicate identifier found for product' in line.lower():
                return True
    except IOError:
        return False

    return False

def _delete_crawl_files(crawl_id):
    try:
        os.unlink(os.path.join(DATA_DIR, '%s_products.csv' % crawl_id))
    except OSError:
        pass
    try:
        os.unlink(os.path.join(DATA_DIR, '%s_changes.csv' % crawl_id))
    except OSError:
        pass

    try:
        os.unlink(os.path.join(DATA_DIR, '%s_changes_old.csv' % crawl_id))
    except OSError:
        pass
    try:
        os.unlink(os.path.join(DATA_DIR, '%s_changes_new.csv' % crawl_id))
    except OSError:
        pass
    try:
        os.unlink(os.path.join(DATA_DIR, 'meta/%s_meta.json' % crawl_id))
    except OSError:
        pass
    try:
        os.unlink(os.path.join(DATA_DIR, 'meta/%s_meta_changes.json' % crawl_id))
    except OSError:
        pass
    try:
        os.unlink(os.path.join(DATA_DIR, 'additional/%s_changes.json' % crawl_id))
    except OSError:
        pass
    try:
        os.unlink(os.path.join(DATA_DIR, '%s_errors.csv' % crawl_id))
    except OSError:
        pass

def _get_disabled_sites(view_hidden=False):
    db_session = DBSession()

    query = [or_(Spider.enabled == False, Spider.automatic_upload == False), Account.enabled == True]
    if not view_hidden:
        query.append(or_(Spider.hide_disabled == False,
                         Spider.hide_disabled == None))

    spiders = db_session.query(Spider).join(Account).filter(*query).options(joinedload('account'))

    return spiders

def _get_enabled_sites():
    db_session = DBSession()

    spiders = db_session.query(Spider).join(Account)\
        .filter(and_(Spider.enabled == True,
                     Account.enabled == True)).options(joinedload('account'))

    return spiders

def db_object_to_dict(obj, attrs):
    return [dict([(attr, getattr(item, attr)) for attr in attrs]) for item in obj]

def get_all_developers():
    db_session = DBSession()

    developers = db_object_to_dict(\
        db_session.query(Developer).filter(Developer.active == True).all(),
        ['id', 'name', 'assembla_id', 'active'])

    return developers

@view_config(route_name='login', renderer='login.mako', permission=Everyone)
def login(request):
    """
    Login page

    :type request: pyramid.request.Request
    """
    came_from = request.params.get('came_from', request.url)
    if not came_from or\
       came_from == request.route_url('login'):
        came_from = request.route_url('home')  # never use the login form itself as came_from

    if 'remember_login' in request.cookies:
        # authenticate user
        login = request.cookies['remember_login']
        headers = remember(request, login)
        raise HTTPFound(location=came_from,
            headers=headers)

    errors = []
    login = ''

    if 'username' in request.POST and 'password' in request.POST:
        login = request.params['username']
        password = request.params['password']

        if is_login_disabled(login):
            errors.append("Login disabled for user %s" % login)
        elif authenticate(request, login, password):
            authenticated = True
        else:
            authenticated = False
            errors.append("Wrong username or password")

        if authenticated:
            response = request.response
            headers = remember(request, login)
            headers = _merge_response_headers(headers, response)
            if 'remember' in request.params:
                response.set_cookie(key='remember_login', value=login, max_age=60 * 60 * 24,
                    expires=datetime.now() + timedelta(days=1))

            # authenticate user
            raise HTTPFound(location=came_from, headers=headers)

    return {
        # specific urls
        'username': login,
        'errors': errors
    }

@view_config(route_name='logout', permission=Authenticated)
def logout(request):
    assembla.forget(request)
    response = request.response
    if 'remember_login' in request.cookies:
        response.delete_cookie('remember_login')
    headers = _merge_response_headers(forget(request), response)
    return HTTPFound(location=request.route_url('home'),
        headers=headers)

@view_config(route_name="home", permission=Authenticated)
def home(request):
    if has_permission('administration', None, request):
        return HTTPFound(location=request.route_url('dashboard'))
    if has_permission('maintenance', None, request):
        return HTTPFound(location=request.route_url('list_all_spiders', _query={'errors': 'real'}))
    if has_permission('deletions_management', None, request):
        return HTTPFound(location=request.route_url('list_deleted_products'))
    return HTTPFound(request.route_url('login'))

@view_config(route_name='dashboard', renderer='dashboard.mako', permission='administration')
def dashboard(request):
    db_session = DBSession()

    possible_count = _count_possible_errors()
    real_count = _count_real_errors()

    disabled_sites = []

    for site in _get_disabled_sites():
        last_crawl = db_session.query(Crawl)\
                .filter(Crawl.spider_id == site.id)\
                .order_by(desc(Crawl.crawl_date)).first()
        if last_crawl:
            if last_crawl.end_time:
                last_updated = last_crawl.end_time.date()
            elif last_crawl.start_time:
                last_updated = last_crawl.start_time.date()
            else:
                last_updated = last_crawl.crawl_date
        else:
            last_updated = None
        disabled_sites.append({'account_name': site.account.name,
                               'site_name': site.name,
                               'site_id': site.id,
                               'auto_upload': site.automatic_upload,
                               'enabled': site.enabled,
                               'last_updated': last_updated,
                               })

    spiders_errors = _get_spiders_errors()

    error_types = {}
    for k, error_type in ERROR_TYPES_DICT.items():
        error_types[error_type] = 0

    developers = {}
    developers_db = db_session.query(Developer).all()
    for dev_db in developers_db:
        developers[dev_db.name] = dev_db.total_assigned

    for spider_error in spiders_errors:
        if spider_error.status == 'real':
            error_types[ERROR_TYPES_DICT[spider_error.error_type]] += 1

    dashboard_menu = Menu()

    return {
        'menu': dashboard_menu.get_iterable(),
        'real_count': real_count,
        'possible_count': possible_count,
        'disabled_sites': sorted(disabled_sites, key=lambda x: x['last_updated'] if x['last_updated'] else date.today()),
        'from_day': date.today() - timedelta(days=7),
        'to_day': date.today(),
        'error_types': error_types.items(),
        'developers': developers.items(),
    }

@view_config(route_name='last_updated_websites_json', renderer='json', permission='administration')
def last_updated_websites_json(request):
    db_session = DBSession()

    last_updated_sites = []

    conn = db_session.connection()

    enabled_sites = conn.execute(text('select s.id from spider s join account a on(s.account_id = a.id) '
        'where s.enabled and (s.crawl_cron is null or s.crawl_cron = \'* * * * *\') and a.enabled and s.id in (select c.spider_id from crawl c join spider s2 on '
        '(c.spider_id = s2.id) join account a2 on (s2.account_id = a2.id) where s2.enabled and a2.enabled '
        'and c.status = \'upload_finished\' group by c.spider_id having date_part(\'day\', now() - max(c.end_time)) >= 2);'))

    for s in enabled_sites:
        last_crawl = db_session.query(Crawl)\
                .filter(Crawl.spider_id == s['id'])\
                .order_by(desc(Crawl.crawl_date)).first()
        last_successful_crawl = db_session.query(Crawl)\
                .filter(and_(Crawl.spider_id == s['id'], Crawl.status == 'upload_finished'))\
                .order_by(desc(Crawl.crawl_date)).first()
        if last_successful_crawl and last_successful_crawl.end_time:
            duration_error_state = datetime.now() - last_successful_crawl.end_time
        else:
            duration_error_state = None

        if duration_error_state and duration_error_state > timedelta(days=2):
            spider = db_session.query(Spider).get(s['id'])
            last_updated = last_successful_crawl.crawl_date
            if spider.error and spider.error.status != 'fixed':
                if spider.error.error_desc:
                    real_error = spider.error.error_desc
                else:
                    real_error = ERROR_TYPES_DICT[spider.error.error_type]
                if spider.error.assigned_to_id:
                    assigned_to = db_session.query(Developer).get(spider.error.assigned_to_id).serialize()
                else:
                    assigned_to = None
            else:
                real_error = ''
                assigned_to = None

            last_updated_sites.append({'priority': spider.priority_possible_errors,
                                       'account_name': spider.account.name,
                                       'site_name': spider.name,
                                       'site_id': spider.id,
                                       'last_updated': last_updated,
                                       'status': last_crawl.status,
                                       'real_error': real_error,
                                       'duration_error_state': str(duration_error_state),
                                       'assign': assigned_to})

    last_updated_sites = sorted(last_updated_sites, key=lambda x: x['last_updated'])
    for site in last_updated_sites:
        site['last_updated'] = site['last_updated'].strftime('%d/%m/%Y')

    return last_updated_sites

@view_config(route_name='admin', renderer='admin.mako', permission='administration')
def admin(request):
    dashboard_menu = Menu()
    dashboard_menu.set_active('admin')
    return {'menu': dashboard_menu.get_iterable()}

@view_config(route_name='admin_proxy', renderer='admin_proxy.mako', permission='administration')
def admin_proxy(request):
    return {}

@view_config(route_name='admin_default', renderer='admin_default.mako', permission='administration')
def admin_default(request):
    return {}

@view_config(route_name='admin_users', renderer='admin_users.mako', permission='administration')
def admin_users(request):
    return {}

@view_config(route_name='admin_maintenance', renderer='admin_maintenance.mako', permission='administration')
def admin_maintenance(request):
    db_session = DBSession()

    spider_errors = [e[0] for e in db_session.query(SpiderError.spider_id).distinct().all()]
    spiders = db_session.query(Spider.id, Spider.name)\
        .filter(Spider.id.in_(spider_errors))
    issues = ERROR_TYPES_DICT.items()
    developers = db_session.query(Developer).filter(Developer.active == True)

    return {'spiders': spiders, 'issues': issues, 'developers': developers}

@view_config(route_name='assembla_authorized', renderer='json', permission='administration')
def assembla_authorized(request):
    if 'assembla' in request.session\
       and 'authorized' in request.session['assembla']\
       and request.session['assembla']['authorized']:
        return {'authorized': True}
    return {'authorized': False}

@view_config(route_name='admin_devs', renderer='admin_devs.mako', permission='administration')
def admin_devs(request):
    return {}

@view_config(route_name='admin_proxy_srv', renderer='json', permission='administration')
def admin_proxy_srv(request):
    pass

@view_config(route_name='admin_default_srv', renderer='json', permission='administration')
def admin_default_srv(request):
    db_session = DBSession()
    spider_defaults = db_session.query(SpiderDefault).first()
    if not spider_defaults:
        spider_defaults = SpiderDefault()
    if request.method == 'POST':
        for k, value in request.POST.items():
            if hasattr(spider_defaults, k):
                if k in ('automatic_upload', 'silent_updates'):
                    setattr(spider_defaults, k, True if value == 'on' else False)
                else:
                    setattr(spider_defaults, k, unicode(value))
            db_session.add(spider_defaults)
    return {
        'automatic_upload': spider_defaults.automatic_upload,
        'silent_updates': spider_defaults.silent_updates,
        'update_percentage_error': spider_defaults.update_percentage_error,
        'additions_percentage_error': spider_defaults.additions_percentage_error,
        'deletions_percentage_error': spider_defaults.deletions_percentage_error,
        'price_updates_percentage_error': spider_defaults.price_updates_percentage_error,
        'additional_changes_percentage_error': spider_defaults.additional_changes_percentage_error,
        'stock_percentage_error': spider_defaults.stock_percentage_error,
        'max_price_change_percentage': spider_defaults.max_price_change_percentage,
        'add_changes_empty_perc': spider_defaults.add_changes_empty_perc,
        'image_url_perc': spider_defaults.image_url_perc,
        'category_change_perc': spider_defaults.category_change_perc,
        'sku_change_perc': spider_defaults.sku_change_perc,
    }

@view_config(route_name='admin_user_srv', renderer='json', permission='administration')
def admin_user_srv(request):
    user_id = int(request.matchdict['user_id'])
    db_session = DBSession()
    user = db_session.query(User).get(int(user_id))
    status = 200
    if '_method' in request.POST:
        method = request.POST.get('_method', 'POST')
        if method not in ('PUT', 'DELETE'):
            return HTTPBadRequest()
        if method == 'DELETE':
            db_session.delete(user)
            status = 204
        else:
            user.username = request.POST['username']
            if request.POST.get('password'):
                user.set_password(request.POST['password'])
            user.name = request.POST['name']
            user.email = request.POST['email']
            db_session.add(user)

            # Clean user groups
            for user_group in db_session.query(UserGroup).filter(UserGroup.username == user.username):
                db_session.delete(user_group)

            groups = request.POST.getall('groups')
            if type(groups) != list:
                groups = [groups]
            for group_name in groups:
                user_group = db_session.query(UserGroup)\
                    .filter(UserGroup.username == user.username,
                            UserGroup.name == group_name)\
                    .first()
                if not user_group:
                    user_group = UserGroup()
                    user_group.username = user.username
                    user_group.name = group_name

                    db_session.add(user_group)

            status = 201

    groups = [g.name for g in db_session.query(Group).all()]
    user_groups = [g.name for g in db_session.query(UserGroup).filter(UserGroup.username == user.username)]
    return {'status': status,
            'data': {'current_username': request.user.username,
                     'current_user': {'username': request.user.username,
                                      'is_admin': request.user.is_admin()},
                     'user': {'id': user.id,
                              'username': user.username,
                              'name': user.name,
                              'email': user.email,
                              'groups': user_groups},
                     'groups': groups}}

@view_config(route_name='admin_users_srv', renderer='json', permission='administration')
def admin_users_srv(request):
    db_session = DBSession()
    if request.method == 'POST' and 'username' in request.POST:
        new_user = User()

        new_user.username = request.POST['username']
        new_user.set_password(request.POST['password'])
        new_user.name = request.POST['name']
        new_user.email = request.POST['email']
        db_session.add(new_user)

        groups = request.POST.getall('groups')
        if type(groups) != list:
            groups = [groups]
        for group_name in groups:
            user_group = db_session.query(UserGroup)\
                .filter(UserGroup.username == new_user.username,
                        UserGroup.name == group_name)\
                .first()
            if not user_group:
                user_group = UserGroup()
                user_group.username = new_user.username
                user_group.name = group_name

                db_session.add(user_group)

    users = []
    users_db = db_session.query(User).all()
    groups = [g.name for g in db_session.query(Group).all()]
    for user_db in users_db:
        user = {
            'id': user_db.id,
            'username': user_db.username,
            'name': user_db.name,
            'email': user_db.email
        }
        user['groups'] = [g.name for g in db_session.query(UserGroup).filter(UserGroup.username == user_db.username).all()]
        users.append(user)

    return {'status': 200, 'data': {'users': users, 'groups': groups,
                                    'current_user': {'username': request.user.username,
                                                     'is_admin': request.user.is_admin()}}}

@view_config(route_name='admin_dev_srv', renderer='json', permission='administration')
def admin_dev_srv(request):

    dev_id = int(request.matchdict['dev_id'])

    db_session = DBSession()

    dev = db_session.query(Developer).get(int(dev_id))

    status = 200
    if '_method' in request.POST:
        method = request.POST.get('_method', 'POST')
        if method not in ('PUT', 'DELETE'):
            return HTTPBadRequest()
        if method == 'DELETE':
            db_session.delete(dev)
            status = 204
        else:
            dev.name = request.POST['name']
            dev.assembla_id = request.POST['assembla_id']
            active_value = request.POST['active']
            dev.active = True if active_value == 'on' else False
            db_session.add(dev)

            status = 201

    assembla_users = assembla.get_users(request)

    return {'status': status,
            'data': {'dev': {'id': dev.id,
                             'name': dev.name,
                             'assembla_id': dev.assembla_id,
                             'active': dev.active},
                     'assembla_users': assembla_users}}

@view_config(route_name='admin_devs_srv', renderer='json', permission='administration')
def admin_devs_srv(request):
    db_session = DBSession()
    if request.method == 'POST' and 'name' in request.POST:
        new_dev = Developer()

        new_dev.name = request.POST['name']
        new_dev.assembla_id = request.POST['assembla_id']
        active_value = request.POST['active']
        new_dev.active = True if active_value == 'on' else False
        db_session.add(new_dev)

    devs = []
    devs_db = db_session.query(Developer).all()
    for dev_db in devs_db:
        dev = {
            'id': dev_db.id,
            'name': dev_db.name,
            'assembla_id': dev_db.assembla_id,
            'active': dev_db.active,
        }
        devs.append(dev)

    return {'status': 200, 'data': {'devs': devs}}

@view_config(route_name='assembla_users', renderer='json', permission='administration')
def assembla_users(request):
    return {'assembla_users': assembla.get_users(request)}

@view_config(route_name='admin_maintenance_srv', renderer='json', permission='administration')
def admin_maintenance_srv(request):
    db_session = DBSession()

    query = request.POST

    filters = {
        'spiders': query.getall('spider'),
        'issues': query.getall('issue'),
        'developers': query.getall('developer'),
        'from': query.get('from'),
        'to': query.get('to'),
        'page': int(query.get('page', 1) or 1),
        'page_size': int(query.get('page_size', 50) or 50),
    }

    spider_errors_query = db_session.query(SpiderError)

    for fld, k in [('spider_id', 'spiders'), ('error_type', 'issues'), ('assigned_to_id', 'developers')]:
        if filters[k]:
            if type(filters[k]) != list:
                filters[k] = list(filters[k])

            spider_errors_query = spider_errors_query\
                .filter(getattr(SpiderError, fld).in_(filters[k]))

    for k in ['from', 'to']:
        if filters[k]:
            try:
                filters[k] = datetime.strptime(filters[k], '%d/%m/%Y')

                time_added_filter = SpiderError.time_added >= filters[k] if k == 'from' else \
                    SpiderError.time_added <= filters[k]
                spider_errors_query = spider_errors_query\
                    .filter(time_added_filter)
            except:
                pass

    # Paging
    current_page = int(filters['page'])
    if current_page > 0:
        page_size = int(filters['page_size'])
        total_count = spider_errors_query.count()
        all_pages = int(ceil(float(total_count) / float(page_size)))
        next_page = current_page + 1 if current_page < all_pages else 0
        prev_page = current_page - 1 if current_page > 1 else 0
        data = spider_errors_query.order_by(desc(SpiderError.time_added)).offset((current_page - 1) * page_size)\
            .limit(page_size)

        paging_size = 15

        first_page = current_page - 5
        first_page = first_page if first_page > 0 else 1
        last_page = first_page + paging_size - 1
        last_page = last_page if last_page < all_pages else all_pages
    else:
        data = spider_errors_query.order_by(desc(SpiderError.time_added))

    issues = []

    for spider_error in data:
        spider = db_session.query(Spider.account_id, Spider.name).filter(Spider.id == spider_error.spider_id).first()
        spider_name = spider.name
        account_name = db_session.query(Account.name).filter(Account.id == spider.account_id).first().name

        issue_type = ERROR_TYPES_DICT[spider_error.error_type]
        if spider_error.error_desc:
            issue_type = spider_error.error_desc

        issues.append({
            'account': account_name,
            'spider': spider_name,
            'issue': issue_type,
            'time_added': spider_error.time_added.strftime('%d/%m/%Y %H:%M'),
            'fixed': True if spider_error.status == 'fixed' else False,
            'time_fixed': spider_error.time_fixed.strftime('%d/%m/%Y %H:%M') if spider_error.time_fixed else '',
            'developer': db_session.query(Developer).get(spider_error.assigned_to_id).name if spider_error.assigned_to_id else '',
        })

    if current_page < 0:
        # Return all pages
        return issues

    return {'status': 200, 'data': {'issues': issues, 'pages': range(first_page, last_page + 1), 'total': total_count,
                                    'page': current_page, 'prev': prev_page, 'next': next_page}}

@view_config(route_name='assign_issue', renderer='assign.mako', permission='administration')
def assign_issue(request):
    site_id = int(request.matchdict['spider_id'])
    db_session = DBSession()
    site_error = db_session.query(SpiderError)\
        .filter(SpiderError.spider_id == site_id,
                SpiderError.status != 'fixed').first()
    if 'dev_id' in request.POST:
        if int(request.POST['dev_id']) != -1:
            developer = db_session.query(Developer).get(int(request.POST['dev_id']))
        else:
            developer = None
        if not site_error:
            site_error = SpiderError()
            site_error.spider_id = site_id
            site_error.status = 'real'
            site_error.error_type = 'maintenance'
            site_error.time_added = datetime.now()

        site_error.assigned_to_id = developer.id if developer else None

        db_session.add(site_error)

        if hasattr(request, 'user') and developer:
            user_activity = UserLog()
            user_activity.username = request.user.username
            user_activity.name = request.user.name
            user_activity.spider_id = site_id
            user_activity.activity = 'Assigned %s' % developer.name
            user_activity.date_time = datetime.now()
            db_session.add(user_activity)

        if developer:
            return Response(json={'site_id': site_id, 'developer': {'id': developer.id, 'name': developer.name}})
        else:
            return Response(json={'site_id': site_id, 'developer': None})

    else:
        if site_error and site_error.assigned_to_id:
            developer = db_session.query(Developer).get(int(site_error.assigned_to_id))
        else:
            developer = None

    return {'site_id': site_id, 'developer': developer, 'developers': get_all_developers()}


@view_config(route_name='spider_notes', renderer='notes.mako', permission='administration')
def spider_notes(request):
    site_id = int(request.matchdict['spider_id'])
    db_session = DBSession()
    if 'note' in request.POST:
        method = request.POST.get('_method', 'POST')
        if method == 'POST':
            new_note = Note()
        elif method == 'PUT' or method == 'DELETE':
            note_id = request.POST.get('id')
            if note_id is not None:
                new_note = db_session.query(Note).get(int(note_id))
            else:
                return HTTPBadRequest()
        else:
            return HTTPBadRequest()
        if method == 'DELETE':
            db_session.delete(new_note)
        else:
            new_note.spider_id = site_id
            new_note.time_added = datetime.now() if method == 'POST' else new_note.time_added
            new_note.text = request.POST['note']
            db_session.add(new_note)
        #if method == 'POST':
        #    return HTTPFound(request.route_url('list_crawls', spider_id=site_id))
    notes = db_session.query(Note).filter(Note.spider_id == site_id)
    return {'site_id': site_id, 'notes': sorted(notes, key=lambda x: x.time_added, reverse=True)}


@view_config(route_name='spider_user_logs', renderer='user_logs.mako', permission='administration')
def spider_user_logs(request):
    site_id = int(request.matchdict['spider_id'])
    page_no = int(request.GET.get('page', 1))
    page_size = 50

    db_session = DBSession()
    uls_query = db_session.query(UserLog).filter(UserLog.spider_id == site_id)
    total_count = uls_query.count()
    prev_page = page_no - 1 if page_no > 1 else 0
    next_page = page_no + 1 if page_no * page_size < total_count else 0
    user_logs = uls_query.order_by(desc(UserLog.date_time)).offset((page_no - 1) * page_size).limit(page_size)
    return {'logs': user_logs,
            'user_log': False,
            'ref_id': site_id,
            'next_page': next_page,
            'prev_page': prev_page}


@view_config(route_name='user_logs', renderer='user_logs.mako', permission='administration')
def user_logs(request):
    user_id = int(request.matchdict['user_id'])
    page_no = int(request.GET.get('page', 1))
    page_size = 50

    db_session = DBSession()
    user_db = db_session.query(User).get(int(user_id))
    uls_query = db_session.query(UserLog).filter(UserLog.username == user_db.username)
    total_count = uls_query.count()
    prev_page = page_no - 1 if page_no > 1 else 0
    next_page = page_no + 1 if page_no * page_size < total_count else 0
    user_logs = uls_query.order_by(desc(UserLog.date_time)).offset((page_no - 1) * page_size).limit(page_size)
    return {'logs': user_logs,
            'user_log': True,
            'ref_id': user_id,
            'next_page': next_page,
            'prev_page': prev_page}


@view_config(route_name='add_note', renderer='addnote.mako', permission='administration')
def spider_notes_add_form(request):
    site_id = int(request.matchdict['spider_id'])
    return {'site_id': site_id}


@view_config(route_name='list_accounts', renderer='list_accounts.mako', permission='administration')
def list_accounts(request):
    dir_accounts = get_accounts()
    accounts = []
    db_session = DBSession()

    for account in dir_accounts:
        name = account[0]
        spiders = account[1]
        db_account = db_session.query(Account).filter(Account.name == name).first()
        member_id = ''
        enabled = False
        if db_account:
            member_id = db_account.member_id
            enabled = db_account.enabled

        accounts.append({'name': name, 'spiders': spiders, 'member_id': member_id, 'enabled': enabled})

    return dict(accounts=sorted(accounts, key=lambda x: x['name']))

@view_config(route_name='list_account_spiders_old', renderer='list_spiders.mako', permission='administration')
def list_account_spiders_old(request):
    db_session = DBSession()
    account_name = request.matchdict.get('account')

    db_account = db_session.query(Account).filter(Account.name == account_name).first()
    if db_account:
        spiders = db_session.query(Spider).filter(Spider.account_id == db_account.id).all()
        db_spiders = [spider.name for spider in spiders]
    else:
        spiders = []
        db_spiders = []

    acc, acc_spiders = get_account(account_name)
    spider_names = [spider_name for spider_name in acc_spiders if spider_name not in db_spiders]

    for spider_name in spider_names:
        spider = db_session.query(Spider).filter(Spider.name == spider_name).first()
        if not spider:
            spider = Spider()
            spider.name = spider_name
        spiders.append(spider)

    for spider in spiders:
        if spider.error and spider.error.status != 'fixed' and spider.error.assigned_to_id:
            spider.assigned_to_id = spider.error.assigned_to_id
            spider.assigned_to_name = db_session.query(Developer).get(spider.assigned_to_id).name
        else:
            spider.assigned_to_id = ''
            spider.assigned_to_name = ''

        spider.logs_url = get_logs_url(request, spider, db_session)

    return dict(account=account_name, spiders=spiders, developers=get_all_developers())

@view_config(route_name='list_account_spiders', renderer='list_spiders_new.mako', permission='administration')
def list_account_spiders(request):
    account_name = request.matchdict.get('account')
    with_errors = request.GET.get('errors')

    if with_errors:
        json_url = request.route_url("list_account_spiders_json", account=account_name, _query={'errors': with_errors})
    else:
        json_url = request.route_url("list_account_spiders_json", account=account_name)

    if 'assembla' in request.session\
       and 'authorized' in request.session['assembla']\
        and request.session['assembla']['authorized']\
        and with_errors == 'real':
        assembla_authorized = True
        assembla_ticket_submit_url = request.route_url("assembla_ticket_submit")
        assembla_authorization_url = ""
    else:
        assembla_authorized = False
        assembla_ticket_submit_url = ""
        assembla_authorization_url = request.route_url('assembla_authorization')

    db_session = DBSession()
    developers = [{'id': d.id, 'name': d.name, 'assembla_id': d.assembla_id} for d in db_session.query(Developer).all()]
    db_session.close()

    return dict(
        account=account_name,
        json_url=json_url,
        show_errors=with_errors,
        developers=json.dumps(developers),
        assembla_authorized=assembla_authorized,
        assembla_ticket_submit_url=assembla_ticket_submit_url,
        assembla_authorization_url=assembla_authorization_url
    )

@view_config(route_name='list_account_spiders_json', permission='maintenance')
def list_account_spiders_json(request):
    account_name = request.matchdict.get('account')
    with_errors = request.GET.get('errors')
    count = request.GET.get('count', None)

    spiders = _get_spiders_list(with_errors, request, count=count, account=account_name)

    json_spiders = json.dumps(spiders, cls=get_sqlalchemy_json_encoder(
        False,
        fields_to_expand=["error"],
        fields_to_ignore=["account", "crawls", "notifications_receivers", "serialize"])
    )

    return Response(json_spiders)

@view_config(route_name='list_all_spiders_old', renderer='list_all_spiders.mako', permission='maintenance')
def list_all_spiders(request):
    with_errors = request.GET.get('errors')
    count = request.GET.get('count', None)

    spiders = _get_spiders_list(with_errors, request, count=count)
    return dict(spiders=spiders, show_errors=with_errors)

@view_config(route_name='list_all_spiders', renderer='list_all_spiders_new.mako', permission='maintenance')
def list_all_spiders_new(request):
    with_errors = request.GET.get('errors')

    if with_errors:
        if with_errors == 'possible':
            json_url = request.route_url("list_all_spiders_json", _query={'errors': with_errors})
        else:
            json_url = request.route_url("list_all_spiders_json", _query={'errors': with_errors})
    else:
        json_url = request.route_url("list_all_spiders_json")

    if 'assembla' in request.session\
       and 'authorized' in request.session['assembla']\
        and request.session['assembla']['authorized']\
        and with_errors == 'real':
        assembla_authorized = True
        assembla_ticket_submit_url = request.route_url("assembla_ticket_submit")
        assembla_authorization_url = ""
    else:
        assembla_authorized = False
        assembla_ticket_submit_url = ""
        assembla_authorization_url = request.route_url('assembla_authorization')

    db_session = DBSession()
    developers = [{'id': d.id, 'name': d.name, 'assembla_id': d.assembla_id} for d in db_session.query(Developer).all()]
    db_session.close()

    return dict(
        json_url=json_url,
        show_errors=with_errors,
        error_types=ERROR_TYPES,
        developers=json.dumps(developers),
        assembla_authorized=assembla_authorized,
        assembla_ticket_submit_url=assembla_ticket_submit_url,
        assembla_authorization_url=assembla_authorization_url
    )


def sql_obj_to_dict(obj):
    fields = {}
    # go through each field in this SQLalchemy class
    for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
        val = obj.__getattribute__(field)

        # is this field another SQLalchemy object, or a list of SQLalchemy objects?
        if isinstance(val.__class__, DeclarativeMeta) or (
            isinstance(val, list) and len(val) > 0 and isinstance(val[0].__class__, DeclarativeMeta)):
            # stop here
            continue

        fields[field] = val
    return fields

def get_sql_obj_fields_list(obj, ignore=None):
    if ignore is None:
        ignore = []
    fields = []
    # go through each field in this SQLalchemy class
    for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
        if field in ignore:
            continue
        val = obj.__getattribute__(field)

        # is this field another SQLalchemy object, or a list of SQLalchemy objects?
        if isinstance(val.__class__, DeclarativeMeta) or (
            isinstance(val, list) and len(val) > 0 and isinstance(val[0].__class__, DeclarativeMeta)):
            # stop here
            continue

        fields.append(field)
    return fields

def jsonify_spiders_list(spiders):
    res = []

    if not spiders:
        return []

    spider_fields_to_ignore = ['notification_receivers', 'error', 'notes', 'crawl_method2', 'scrapely_data', 'users_logs', 'serialize']

    fields = get_sql_obj_fields_list(spiders[0], ignore=spider_fields_to_ignore)
    error_fields = None
    delistes_duplicate_error_fields = None

    for s in spiders:
        s_dict = {field: getattr(s, field, None) for field in fields}
        if s.error:
            if error_fields is None:
                error_fields = get_sql_obj_fields_list(s.error)
            error_dict = {field: getattr(s.error, field, None) for field in error_fields}
            s_dict['error'] = error_dict
        else:
            s_dict['error'] = None
        if s.delistes_duplicate_errors:
            if delistes_duplicate_error_fields is None:
                delistes_duplicate_error_fields = get_sql_obj_fields_list(s.delistes_duplicate_errors[0])
            s_dict['delistes_duplicate_errors'] = [{field: getattr(e, field, None) for field in delistes_duplicate_error_fields} for e in s.delistes_duplicate_errors]
        else:
            s_dict['delistes_duplicate_errors'] = []
        # s_dict = sql_obj_to_dict(s)
        # s_dict['error'] = sql_obj_to_dict(s.error)

        res.append(s_dict)

    return json.dumps(res, cls=DatetimeJSONEncoder)


@view_config(route_name='list_all_spiders_json', permission='maintenance')
def list_all_spiders_json(request):
    with_errors = request.GET.get('errors')
    count = request.GET.get('count', None)

    spiders = _get_spiders_list(with_errors, request, count=count)

    json_spiders = json.dumps(spiders, cls=get_sqlalchemy_json_encoder(
        False,
        fields_to_expand=["error"],
        fields_to_ignore=["account", "crawls", "notifications_receivers", "serialize"])
    )

    return Response(json_spiders)

@view_config(route_name='config_account', renderer='config_account.mako', permission='administration')
def config_account(request):
    account_name = request.matchdict['account']
    db_session = DBSession()

    account = db_session.query(Account)\
                        .filter(Account.name == account_name).first()
    if not account:
        account = Account()
        account.name = account_name
        account.enabled = True
        account.upload_new_system = False
        account.upload_keter_system = False
        account.upload_new_and_old = False

    for status in UI_CRAWL_STATUSES:
        receivers = db_session.query(NotificationReceiver)\
                              .filter(and_(NotificationReceiver.account_id == account.id,
                                           NotificationReceiver.status == status,
                                           NotificationReceiver.spider_id == None)).all()

        emails = ','.join([receiver.email for receiver in receivers])
        setattr(account, status + '_emails', emails)

    upload_destinations = db_session.query(UploadDestination).order_by(UploadDestination.id).all()

    # add upload destinations values to form
    upload_destinations_defaults = {}
    for upload_dst in upload_destinations:
        if account and upload_dst in account.upload_destinations:
            upload_destinations_defaults['upload_to_' + upload_dst.name] = True
        else:
            upload_destinations_defaults['upload_to_' + upload_dst.name] = False

    defaults = {'enabled': True}

    # merge defaults dicts
    defaults = dict(upload_destinations_defaults.items() + defaults.items())

    form = Form(request, schema=AccountSchema, obj=account,
                defaults=defaults)

    if form.validate():
        form.bind(account)

        for upload_dst in upload_destinations:
            if form.data['upload_to_' + upload_dst.name]:
                if not upload_dst in account.upload_destinations:
                    account.upload_destinations.append(upload_dst)
            else:
                if upload_dst in account.upload_destinations:
                    account.upload_destinations.remove(upload_dst)

        if len(account.upload_destinations) < 1:
            # old_system_dst = db_session.query(UploadDestination).filter(UploadDestination.name == 'old_system').first()
            # if old_system_dst:
            #     account.upload_destinations.append(old_system_dst)
            # else:
            new_system_dst = db_session.query(UploadDestination).filter(UploadDestination.name == 'new_system').first()
            if new_system_dst:
                account.upload_destinations.append(new_system_dst)

        db_session.add(account)

        if not account.enabled:
            account_spiders = db_session.query(Spider).filter(Spider.account_id == account.id, Spider.enabled == True)
            for spider in account_spiders:
                spider.enabled = False
                db_session.add(spider)

        # delete old notification receivers for this account
        db_session.query(NotificationReceiver)\
                  .filter(and_(NotificationReceiver.account_id == account.id,
                               NotificationReceiver.spider_id == None)).delete()
        # set the new notification receivers
        for status in UI_CRAWL_STATUSES:
            emails = getattr(account, status + '_emails') or []
            for email in emails:
                receiver = NotificationReceiver(email, status, account, spider=None)
                db_session.add(receiver)

        return HTTPFound('/productspiders/crawlers')

    return dict(account=account, renderer=FormRenderer(form),
                upload_destinations=upload_destinations,
                statuses=UI_CRAWL_STATUSES, statuses_labels=STATUSES_LABELS)

@view_config(route_name='config_spider', renderer='config_spider.mako', permission='administration')
def config_spider(request):
    spider_name = request.matchdict['spider']
    account_name = request.matchdict['account']
    db_session = DBSession()

    spider = db_session.query(Spider)\
                       .filter(Spider.name == spider_name).first()

    spider_default = db_session.query(SpiderDefault).first()

    if not spider:
        spider = Spider()
        spider.timezone = 'GMT'
        spider.name = spider_name
        spider.enabled = True
        spider.automatic_upload = True if not spider_default else spider_default.automatic_upload
        spider.use_proxies = False
        spider.proxy_service_enabled = False
        spider.use_tor = False
        spider.tor_renew_on_retry = False
        spider.use_cache = False
        spider.cache_expiration = 86400
        spider.upload_testing_account = False
        spider.enable_metadata = False
        spider.reviews_mandatory = False
        spider.silent_updates = True if not spider_default else spider_default.silent_updates
        spider.max_price_change_percentage = 80 if not spider_default else spider_default.max_price_change_percentage
        spider.update_percentage_error = 80 if not spider_default else spider_default.update_percentage_error
        spider.additions_percentage_error = 10 if not spider_default else spider_default.additions_percentage_error
        spider.deletions_percentage_error = 10 if not spider_default else spider_default.deletions_percentage_error
        spider.price_updates_percentage_error = 50 if not spider_default else spider_default.price_updates_percentage_error
        spider.additional_changes_percentage_error = 10 if not spider_default else spider_default.additional_changes_percentage_error
        spider.stock_percentage_error = 10 if not spider_default else spider_default.stock_percentage_error
        spider.add_changes_empty_perc = 10 if not spider_default else spider_default.add_changes_empty_perc
        spider.image_url_perc = 50 if not spider_default else spider_default.image_url_perc
        spider.category_change_perc = 10 if not spider_default else spider_default.category_change_perc
        spider.sku_change_perc = 50 if not spider_default else spider_default.sku_change_perc
        spider.enable_multicrawling = False
        spider.concurrent_requests = 8
        spider.disable_cookies = False
        spider.crawl_minute = 0
        spider.priority_possible_errors = 0
        spider.automatic_retry_enabled = True
        spider.automatic_retries_max = 2

    prev_automatic_upload = spider.automatic_upload
    prev_spider_enabled = spider.enabled

    account = db_session.query(Account).filter(Account.name == account_name).first()
    for status in UI_CRAWL_STATUSES:
        receivers = []
        if account and spider.id:
            receivers = db_session.query(NotificationReceiver)\
                                  .filter(and_(NotificationReceiver.account_id == account.id,
                                               NotificationReceiver.status == status,
                                               NotificationReceiver.spider_id == spider.id)).all()

        emails = ','.join([receiver.email for receiver in receivers])
        setattr(spider, status + '_emails', emails)

    # convert expiration time to hours
    spider.cache_expiration /= 3600

    form = Form(request, schema=SpiderSchema, obj=spider,
                defaults={'enabled': True, 'automatic_upload': True, 'crawl_minute': 0})

    if form.validate():
        account = db_session.query(Account).filter(Account.name == account_name).first()
        if not account:
            account = Account()
            account.name = account_name
            account.enabled = True
            db_session.add(account)

        if not spider.account:
            spider.account = account

        form.bind(spider)
        if spider.update_percentage_error:
            spider.update_percentage_error = str(spider.update_percentage_error)
        if spider.additions_percentage_error:
            spider.additions_percentage_error = str(spider.additions_percentage_error)
        if spider.deletions_percentage_error:
            spider.deletions_percentage_error = str(spider.deletions_percentage_error)
        if spider.price_updates_percentage_error:
            spider.price_updates_percentage_error = str(spider.price_updates_percentage_error)
        if spider.additional_changes_percentage_error:
            spider.additional_changes_percentage_error = str(spider.additional_changes_percentage_error)

        if spider.cache_storage == "":
            spider.cache_storage = None

        if spider.max_price_change_percentage:
            spider.max_price_change_percentage = str(spider.max_price_change_percentage)

        if spider.price_conversion_rate:
            spider.price_conversion_rate = str(spider.price_conversion_rate)

        if prev_automatic_upload != spider.automatic_upload and hasattr(request, 'user'):
            user_activity = UserLog()
            user_activity.username = request.user.username
            user_activity.name = request.user.name
            user_activity.spider_id = spider.id
            if spider.automatic_upload:
                user_activity.activity = 'Automatic upload enabled'
            else:
                user_activity.activity = 'Automatic upload disabled'
            user_activity.date_time = datetime.now()
            db_session.add(user_activity)

        if prev_spider_enabled != spider.enabled and hasattr(request, 'user'):
            user_activity = UserLog()
            user_activity.username = request.user.username
            user_activity.name = request.user.name
            user_activity.spider_id = spider.id
            if spider.enabled:
                user_activity.activity = 'Site enabled'
            else:
                user_activity.activity = 'Site disabled'
            user_activity.date_time = datetime.now()
            db_session.add(user_activity)

        # convert spider expiration from hours to seconds
        spider.cache_expiration *= 3600

        db_session.add(spider)

        # delete old notification receivers for this account
        db_session.query(NotificationReceiver)\
                  .filter(and_(NotificationReceiver.account_id == account.id,
                               NotificationReceiver.spider_id == spider.id)).delete()

        # set the new notification receivers
        for status in UI_CRAWL_STATUSES:
            emails = getattr(spider, status + '_emails') or []
            for email in emails:
                receiver = NotificationReceiver(email, status, account, spider)
                db_session.add(receiver)

        if request.params.get('crawl_method'):
            crawl_method = spider.crawl_method2
            if not crawl_method:
                crawl_method = CrawlMethod()
                spider.crawl_method2 = crawl_method
            crawl_method.crawl_method = request.params['crawl_method']
            params = {}
            for field, value in request.params.items():
                if field.startswith(crawl_method.crawl_method):
                    field_name = field[len(crawl_method.crawl_method) + 1:]
                    if 'postprocess' in CRAWL_METHOD_PARAMS[crawl_method.crawl_method][field_name]:
                        func = CRAWL_METHOD_PARAMS[crawl_method.crawl_method][field_name]['postprocess']
                        if callable(func):
                            value = func(value)
                    params[field_name] = value
            crawl_method.params = params
            db_session.add(crawl_method)
        else:
            crawl_method = spider.crawl_method2
            if crawl_method:
                db_session.delete(crawl_method)

        return HTTPFound(request.route_url('list_account_spiders_old', account=account_name))
    else:
        db_session.rollback()

    proxy_lists = db_session.query(ProxyList).all()
    proxymesh_ids = [x.id for x in proxy_lists if 'proxymesh' in x.proxies]
    spider_uses_proxymesh = spider.proxy_list_id in proxymesh_ids
    spider_proxymesh_proxy_name = [x.name for x in proxy_lists if x.id == spider.proxy_list_id][0] if spider_uses_proxymesh else ''
    worker_servers = db_session.query(WorkerServer).all()
    additional_fields_groups = db_session.query(AdditionalFieldsGroup).all()

    # Proxy service
    proxy_service_data = {'profiles': [],
                          'types': [],
                          'locations': []}
    try:
        for data_key in proxy_service_data.keys():
            url = urljoin(PROXY_SERVICE_HOST, data_key)
            r = requests.get(url, auth=HTTPBasicAuth(PROXY_SERVICE_USER, PROXY_SERVICE_PSWD))
            data = r.json()
            proxy_service_data[data_key].extend(data['data'])
    except:
        pass

    proxy_service_data['algorithms'] = PROXY_SERVICE_ALGORITHM_CHOICES

    return dict(account=account_name, spider=spider, renderer=FormRenderer(form),
                statuses=UI_CRAWL_STATUSES, statuses_labels=STATUSES_LABELS, days=DAYS_DATA, proxy_lists=proxy_lists,
                proxymesh_ids=proxymesh_ids, spider_uses_proxymesh=spider_uses_proxymesh,
                spider_proxymesh_proxy_name=spider_proxymesh_proxy_name,
                worker_servers=worker_servers, additional_fields_groups=additional_fields_groups,
                crawl_methods=CRAWL_METHODS.keys(), crawl_method_params=CRAWL_METHOD_PARAMS, proxy_service=proxy_service_data,
                cache_storages=cache_storages, timezones=TIMEZONES)

@view_config(route_name='list_crawls', renderer='list_crawls.mako', permission='maintenance')
def list_crawls(request):
    db_session = DBSession()
    spider_id = request.matchdict['spider_id']
    spider = db_session.query(Spider).get(spider_id)

    if not spider:
        return HTTPFound('/productspiders')

    if 'reverse' in request.params and request.params['reverse'] == '1':
        spider.crawls = sorted(spider.crawls, key=lambda x: (x.crawl_date, x.id), reverse=True)
    else:
        spider.crawls = sorted(spider.crawls, key=lambda x: (x.crawl_date, x.id), reverse=False)

    for crawl in spider.crawls:
        if crawl.worker_server_id:
            crawl.worker_server = db_session.query(WorkerServer).get(crawl.worker_server_id).name
        else:
            crawl.worker_server = 'Default'
        crawl.started = ''
        crawl.ended = ''
        if crawl.start_time:
            crawl.started = crawl.start_time.strftime('%Y-%m-%d %H:%M')
        if crawl.end_time:
            crawl.ended = crawl.end_time.strftime('%Y-%m-%d %H:%M')

        crawl.time_taken = ''
        if crawl.start_time and crawl.end_time:
            crawl.time_taken = str(crawl.end_time - crawl.start_time).split('.')[0]

    return dict(spider=spider)

@view_config(route_name='list_products', renderer='list_products.mako', permission='maintenance')
def list_products(request):
    db_session = DBSession()
    crawl_id = request.matchdict['crawl_id']
    crawl = db_session.query(Crawl).get(crawl_id)

    if not crawl:
        return HTTPFound('/productspiders')

    with open(os.path.join(DATA_DIR, '%s_products.csv' % crawl.id)) as f:
        reader = csv.DictReader(f)
        products = [row for row in reader]

    return dict(crawl=crawl, products=products)

@view_config(route_name='list_products_paged', renderer='list_products.mako', permission='maintenance')
def list_products_paged(request):
    db_session = DBSession()
    crawl_id = request.matchdict['crawl_id']
    crawl = db_session.query(Crawl).get(crawl_id)

    if not crawl:
        return HTTPFound('/productspiders')

    per_page = 100

    page = int(request.GET.get('page', 1))
    start = (page - 1) * per_page

    end = start + per_page

    pages_count = (crawl.products_count / per_page) + 1

    products = []
    with open(os.path.join(DATA_DIR, '%s_products.csv' % crawl.id)) as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if start <= i < end:
                products.append(row)
            if i > end:
                break
        # products = [row for row in reader]

    return dict(crawl=crawl, products=products, pages_count=pages_count, page=page)

@view_config(route_name='download_products', permission='maintenance')
def download_products(request):
    db_session = DBSession()
    crawl_id = request.matchdict['crawl_id']
    crawl = db_session.query(Crawl).get(crawl_id)
    spider = db_session.query(Spider).get(crawl.spider_id)

    if not crawl:
        return HTTPFound('/productspiders')

    with open(os.path.join(DATA_DIR, '%s_products.csv' % crawl.id)) as f:
        r = Response(f.read(), content_type='text/csv')
        r.headers['Content-Disposition'] = 'attachment; filename=%s_%s.csv' % (spider.website_id, crawl.id)
        return r

@view_config(route_name='list_changes', renderer='list_changes.mako', permission='maintenance')
def list_changes(request):
    return _get_changes(request)

@view_config(route_name='list_additions', renderer='list_changes.mako', permission='maintenance')
def list_additions(request):
    return _get_changes(request, 'addition')

@view_config(route_name='list_deletions', renderer='list_changes.mako', permission='maintenance')
def list_deletions(request):
    return _get_changes(request, 'deletion')

@view_config(route_name='list_updates', renderer='list_changes.mako', permission='maintenance')
def list_updates(request):
    return _get_changes(request, ('update', 'silent_update'))

@view_config(route_name='list_changes_paged', renderer='list_changes.mako', permission='maintenance')
def list_changes_paged(request):
    return _get_changes_paged(request)

@view_config(route_name='list_additions_paged', renderer='list_changes.mako', permission='maintenance')
def list_additions_paged(request):
    return _get_changes_paged(request, 'addition')

@view_config(route_name='list_deletions_paged', renderer='list_changes.mako', permission='maintenance')
def list_deletions_paged(request):
    return _get_changes_paged(request, 'deletion')

@view_config(route_name='list_updates_paged', renderer='list_changes.mako', permission='maintenance')
def list_updates_paged(request):
    return _get_changes_paged(request, ('update', 'silent_update'))

@view_config(route_name='set_crawl_valid', renderer='json', permission='administration')
def set_crawl_valid(request):
    if request.method == 'POST':
        db_session = DBSession()
        crawl_id = int(request.POST.get('crawl_id'))
        crawl = db_session.query(Crawl).get(crawl_id)
        try:
            has_dups = has_duplicate_identifiers(crawl.id)
        except:
            has_dups = False

        if crawl and has_dups:
            return {'error': 'The crawl cannot be set as valid because it has duplicate identifiers'}

        if crawl and crawl.status == 'errors_found':
            crawl.status = 'processing_finished'
            crawl.error_message = None
            spider = db_session.query(Spider).get(crawl.spider_id)
            spider.rerun = False
            db_session.add(spider)

            # Remove Delisted Duplicates errors
            db_session.query(DelistedDuplicateError)\
                .filter(DelistedDuplicateError.crawl_id == crawl_id,
                        DelistedDuplicateError.fixed != True)\
                .delete()

            if hasattr(request, 'user'):
                user_activity = UserLog()
                user_activity.username = request.user.username
                user_activity.name = request.user.name
                user_activity.spider_id = spider.id
                user_activity.activity = 'Set as valid'
                user_activity.date_time = datetime.now()
                db_session.add(user_activity)

    return {}

@view_config(route_name='delete_crawl', renderer='string', permission='administration')
def delete_crawl(request):
    if request.method == 'POST':
        db_session = DBSession()
        crawl_id = int(request.POST.get('crawl_id'))
        crawl = db_session.query(Crawl).get(crawl_id)
        if crawl:
            _delete_crawl_files(crawl.id)
            db_session.query(DeletionsReview).filter(DeletionsReview.crawl_id == crawl.id).delete()
            invalid_crawl = request.POST.get('invalid')
            if invalid_crawl:
                crawl.retry = True
                crawl.status = 'retry'
                crawl_history = db_session.query(CrawlHistory)\
                    .filter(CrawlHistory.crawl_id == crawl_id)\
                    .order_by(desc(CrawlHistory.start_time)).first()
                if crawl_history:
                    discarted_reason = request.POST.get('reason')
                    crawl_history.discarted = True
                    crawl_history.discarted_reason = discarted_reason
                    db_session.add(crawl_history)
                # User log
                if hasattr(request, 'user'):
                    user_activity = UserLog()
                    user_activity.username = request.user.username
                    user_activity.name = request.user.name
                    user_activity.spider_id = crawl.spider_id
                    discarted_reason = request.POST.get('reason')
                    if discarted_reason:
                        user_activity.activity = 'Delete invalid crawl, reason (%s)' % discarted_reason
                    else:
                        user_activity.activity = 'Delete invalid crawl, no reason specified'
                    user_activity.date_time = datetime.now()
                    db_session.add(user_activity)
            else:
                db_session.delete(crawl)

    return ''

@view_config(route_name='delete_crawls', renderer='string', permission='administration')
def delete_crawls(request):
    if request.method == 'POST':
        db_session = DBSession()
        spider_id = int(request.POST.get('spider_id'))
        delete_last_one = int(request.POST.get('delete_last_one'))
        spider = db_session.query(Spider).get(spider_id)
        if spider:
            if delete_last_one:
                crawls = spider.crawls[:]
            else:
                crawls = spider.crawls[:-1]
            crawls.reverse()
            for crawl in crawls:
                _delete_crawl_files(crawl.id)
                db_session.query(DeletionsReview).filter(DeletionsReview.crawl_id == crawl.id).delete()
                db_session.delete(crawl)

    return ''

@view_config(route_name='upload_changes', renderer='string', permission='administration')
def upload_changes_view(request):
    if request.method == 'POST':
        db_session = DBSession()
        spider_id = int(request.POST.get('spider_id'))
        real_upload = request.POST.get('real_upload', '1')
        spider = db_session.query(Spider).get(spider_id)
        if spider and spider.crawls:
            # upload
            uploader = Uploader()
            try:
                if real_upload == '1':
                    upload_changes(uploader, spider)

                spider.crawls[-1].status = 'upload_finished'
                spider.crawls[-1].uploaded_time = datetime.now()
            except UploaderException:
                spider.crawls[-1].status = 'upload_errors'

    return ''

@view_config(route_name='upload_crawl_changes', renderer='string', permission='administration')
def upload_crawl_changes_view(request):
    if request.method == 'POST':
        db_session = DBSession()
        crawl_id = int(request.POST.get('crawl_id'))
        crawl = db_session.query(Crawl).get(crawl_id)
        if crawl:
            # upload
            uploader = Uploader()
            try:
                upload_crawl_changes(uploader, crawl)

                crawl.status = 'upload_finished'
                crawl.uploaded_time = datetime.now()
            except UploaderException:
                crawl.status = 'upload_errors'

    return ''

@view_config(route_name='delete_changes', renderer='string', permission='administration')
def delete_changes(request):
    if request.method == 'POST':
        db_session = DBSession()
        crawl_id = int(request.POST.get('crawl_id'))
        crawl = db_session.query(Crawl).get(crawl_id)
        if crawl:
            f = open(os.path.join(DATA_DIR, '%s_changes.csv' % crawl.id), 'w')
            f.close()

        crawl.changes_count = 0

    return ''

@view_config(route_name='compute_changes', renderer='string', permission='administration')
def compute_changes(request):
    if request.method == 'POST':
        db_session = DBSession()
        crawl_id = request.POST.get('crawl_id')
        spider_id = request.POST.get('spider_id', '')

        if spider_id and not crawl_id:
            spider_id = int(spider_id)
            crawls = db_session.query(Crawl).filter(Crawl.spider_id == spider_id)\
                                            .order_by(Crawl.crawl_date, Crawl.id).all()
        else:
            crawl_id = int(crawl_id)
            crawls = [db_session.query(Crawl).get(crawl_id)]


        for crawl in crawls:
            previous_crawl = db_session.query(Crawl)\
                                       .filter(and_(Crawl.spider_id == crawl.spider_id,
                                                    Crawl.id < crawl.id))\
                                               .order_by(desc(Crawl.crawl_date), desc(Crawl.id)).first()

            updater = ProductsUpdater(db_session, MetadataUpdater())

            def dummy():
                pass

            with open(os.path.join(DATA_DIR, '%s_products.csv' % crawl.id)) as f:
                reader = csv.DictReader(f)
                products = [row for row in reader]

            old_products = []
            if previous_crawl:
                with open(os.path.join(DATA_DIR, '%s_products.csv' % previous_crawl.id)) as f:
                    reader = csv.DictReader(f)
                    old_products = [row for row in reader]

            db_session.commit = dummy
            changes, additions, deletions, updates = updater.compute_changes(crawl.id, old_products, products,
                                                                             crawl.spider.silent_updates)
            additional_changes = updater.compute_additional_changes(crawl.id, old_products, products)

            path_new = os.path.join(DATA_DIR, '%s_changes_new.csv' % crawl.id)
            path_additional = os.path.join(DATA_DIR, 'additional/%s_changes.json-lines' % crawl.id)
            export_changes_new(path_new, changes, crawl.spider.website_id)
            '''
            export_changes(path_old, changes, crawl.crawl_date,
                           crawl.spider.website_id,
                           crawl.spider.account.member_id, crawl.spider.upload_testing_account)
            '''
            export_additional_changes(path_additional, additional_changes)

            spider = crawl.spider
            if spider.enable_metadata:
                # compute metadata changes
                meta_db = MetadataDB(db_session, crawl.id)
                db_session.flush()
                old_products = []
                if previous_crawl:
                    filename, file_format = get_crawl_meta_file(previous_crawl.id, DATA_DIR)
                    old_products = _get_products_metadata(filename, file_format, metadata_db=meta_db,
                                                          crawl_id=previous_crawl.id)

                filename, file_format = get_crawl_meta_file(crawl.id, DATA_DIR)

                products = _get_products_metadata(filename, file_format, metadata_db=meta_db,
                                                  crawl_id=crawl.id)

                products = updater.merge_products(old_products, products, meta_db, crawl.id, previous_crawl.id
                                                  if previous_crawl else None)
                export_metadata(os.path.join(DATA_DIR + '/meta', '%s_meta.json-lines' % crawl.id), products,
                                meta_db, crawl.id)
                changes = updater.compute_metadata_changes(crawl.id, old_products, products, meta_db, crawl.id,
                                                           previous_crawl.id if previous_crawl else None)

                export_metadata_changes(os.path.join(DATA_DIR + '/meta', '%s_meta_changes.json-lines' % crawl.id), changes)


    return ''

@view_config(route_name='manage', renderer='manage.mako', permission='administration')
def manage(request):
    db_session = DBSession()
    spiders = db_session.query(Spider).join(Account)\
                        .filter(and_(Spider.enabled == True, Account.enabled == True)).all()
    spiders = sorted([spider.name for spider in spiders])

    return dict(spiders=spiders)


@view_config(route_name='run_crawl', renderer='string', permission='administration')
def run_crawl(request):
    db_session = DBSessionSimple()

    # db_session.commit = lambda: db_session.flush(); transaction.commit()
    spider = request.POST.get('spider')
    spider = [spider] if spider else None
    force = bool(request.POST.get('force'))

    if spider is not None:
        spider_db = db_session.query(Spider).filter(Spider.name.in_(spider)).first()
        if spider_db:
            last_crawl = db_session.query(Crawl)\
                .filter(Crawl.spider_id == spider_db.id)\
                .order_by(Crawl.crawl_date.desc(),
                          desc(Crawl.id)).limit(1).first()
            if (not last_crawl) or (last_crawl and last_crawl.status == 'upload_finished'):
                schedule_spiders(db_session, spider, force)

    return ''

@view_config(route_name='run_upload', renderer='string', permission='administration')
def run_upload(request):
    db_session = DBSession()
    db_session.commit = lambda: True

    upload_crawls(db_session)

    return ''

@view_config(route_name='set_ids', renderer='string', permission='administration')
def set_skus_as_identifiers(request):
    crawl_id = request.POST.get('crawl_id')

    if not crawl_id or not crawl_id.isdigit():
        return ''

    f = open(os.path.join(DATA_DIR, '%s_products.csv' % crawl_id))
    reader = csv.reader(f)
    with TemporaryFile() as temp:
        writer = csv.writer(temp)

        header = reader.next()
        for row in reader:
            final_row = row[:]
            if final_row[1]:
                final_row[0] = final_row[1]

            writer.writerow(final_row)

        temp.seek(0)
        f.close()
        with open(os.path.join(DATA_DIR, '%s_products.csv' % crawl_id), 'w') as f:
            f.write(','.join(header) + '\n')
            for row in temp:
                f.write(row)

@view_config(route_name='set_updates_silent', renderer='string', permission='administration')
def set_updates_silent(request):
    crawl_id = request.POST.get('crawl_id')
    line = request.POST.get('line')
    if line:
        line = int(line)

    if not crawl_id or not crawl_id.isdigit():
        return ''

    f = open(os.path.join(DATA_DIR, '%s_changes.csv' % crawl_id))
    reader = csv.reader(f)
    with TemporaryFile() as temp:
        writer = csv.writer(temp)
        header = reader.next()
        for i, row in enumerate(reader):
            if row[8] == 'updated' and (line is None or i == line):
                row[8] = 'normal'

            writer.writerow(row)

        temp.seek(0)
        f.close()
        with open(os.path.join(DATA_DIR, '%s_changes.csv' % crawl_id), 'w') as f:
            f.write(','.join(header) + '\n')
            for row in temp:
                f.write(row)

@view_config(route_name='show_errors', renderer='errors.mako', permission='maintenance')
def show_errors(request):
    crawl_id = int(request.matchdict['crawl_id'])
    db_session = DBSession()

    errors = []
    all_errors = []
    error_groups = []
    error_codes_filtered = []
    spider_name = ''
    crawl_method = ''
    crawl = db_session.query(Crawl).get(crawl_id)
    if crawl:
        errors = _get_errors(crawl_id)

    spider_doc = None
    if errors:
        crawl_method = 'Normal run'
        spider = db_session.query(Spider).get(crawl.spider_id)
        spider_name = spider.name
        if crawl.stats and crawl.stats.stats_json:
            crawl_stats = json.loads(crawl.stats.stats_json)
            if crawl_stats.get('BSM', False):
                if not crawl_stats['full_run']:
                    crawl_method = 'Simple run'

        for error_group in db_session.query(SpiderErrorGroup):
            errors_filtered = []
            for error_type in error_group.error_types:
                for e in errors:
                    if e['code'] and int(e['code']) == error_type.code:
                        e['severity_level'] = error_type.severity_level
                        errors_filtered.append(e)
                        all_errors.append(e)
                error_codes_filtered.append(error_type.code)
            error_groups.append({'name': error_group.name, 'errors': errors_filtered})
        spider_doc = request.route_url('show_doc', account=spider.account.name, spider=spider.name)

    uncategorized_errors = []
    for e in errors:
        error_code = e.get('code')
        if not error_code or (error_code and int(error_code) not in error_codes_filtered):
            e['severity_level'] = 3
            uncategorized_errors.append(e)
            all_errors.append(e)

    all_errors.sort(key=lambda e: e['severity_level'])

    return {'spider_name': spider_name,
            'crawl_method': crawl_method,
            'all_errors': all_errors,
            'error_groups': error_groups,
            'uncategorized_errors': uncategorized_errors,
            'doc_url': spider_doc}

@view_config(route_name='get_error_message', renderer='json', permission='maintenance')
def get_error_message(request):
    crawl_id = int(request.matchdict['crawl_id'])
    db_session = DBSession()

    errors = None
    crawl = db_session.query(Crawl).get(crawl_id)

    if crawl:
        errors = _get_errors(crawl_id)

    if errors:
        errors = [x['message'] for x in errors]
        error_message = "\n".join(errors)
    else:
        error_message = ''

    return dict(error_message=error_message)

@view_config(route_name='metadata', renderer='string', permission='maintenance')
def view_metadata(request):
    crawl_id = int(request.matchdict['crawl_id'])
    db_session = DBSession()

    crawl = db_session.query(Crawl).get(crawl_id)

    if crawl and crawl.status not in ['scheduled', 'running']:
        try:
            filename, file_format = get_crawl_meta_file(crawl.id, DATA_DIR)
            if not filename:
                return ''
            meta = _get_metadata_simple(filename, file_format)
        except IOError:
            meta = {}
        return json.dumps(meta, sort_keys=True, indent=4)

    return ''

@view_config(route_name='metadata_changes', renderer='string', permission='maintenance')
def view_metadata_changes(request):
    crawl_id = int(request.matchdict['crawl_id'])
    db_session = DBSession()

    crawl = db_session.query(Crawl).get(crawl_id)

    if crawl and crawl.status not in ['scheduled', 'running']:
        try:
            filename, file_format = get_crawl_meta_changes_file(crawl.id, DATA_DIR)
            if not filename:
                return ''
            meta = _get_metadata_simple(filename, file_format)
        except IOError:
            meta = {}

        return json.dumps(meta, sort_keys=True, indent=4)

    return ''

@view_config(route_name='disable_account', renderer='json', permission='administration')
def disable_account(request):
    if request.method == 'POST':
        account_name = request.POST.get('account')
        db_session = DBSession()

        account = db_session.query(Account) \
            .filter(Account.name == account_name).first()

        if account:
            if account.enabled:
                account.enabled = False
                db_session.add(account)

                account_spiders = db_session.query(Spider).filter(Spider.account_id == account.id, Spider.enabled == True)
                for spider in account_spiders:
                    spider.enabled = False
                    db_session.add(spider)

                notifier = EmailNotifier(SMTP_USER, SMTP_PASS,
                                         SMTP_FROM, SMTP_HOST,
                                         SMTP_PORT)
                notifier.send_notification(account_status_change_receivers,
                                           'Account %s (id: %s) is disabled' % (account.name, account.id),
                                           'Account %s (id: %s) is disabled' % (account.name, account.id))
                return {
                    'status': 'OK'
                }
            else:
                return {
                    'status': 'error',
                    'error': 'Account already disabled'
                }
        else:
            return {
                'status': 'error',
                'error': 'Account not found'
            }
    else:
        return {
            'status': 'error',
            'error': 'wrong HTTP method'
        }

@view_config(route_name='enable_account', renderer='json', permission='administration')
def enable_account(request):
    if request.method == 'POST':
        account_name = request.POST.get('account')
        db_session = DBSession()

        account = db_session.query(Account) \
            .filter(Account.name == account_name).first()

        if account:
            if not account.enabled:
                account.enabled = True
                db_session.add(account)

                notifier = EmailNotifier(SMTP_USER, SMTP_PASS,
                                         SMTP_FROM, SMTP_HOST,
                                         SMTP_PORT)
                notifier.send_notification(account_status_change_receivers,
                                           'Account %s (id: %s) is enabled' % (account.name, account.id),
                                           'Account %s (id: %s) is enabled' % (account.name, account.id))
                return {
                    'status': 'OK'
                }
            else:
                return {
                    'status': 'error',
                    'error': 'Account already enabled'
                }
        else:
            return {
                'status': 'error',
                'error': 'Account not found'
            }
    else:
        return {
            'status': 'error',
            'error': 'wrong HTTP method'
        }

@view_config(route_name='change_spider_error_status', renderer='json', permission='administration')
def change_spider_error_status(request):
    if request.method == 'POST':
        status = request.POST.get('status', None)
        spider_id = int(request.POST.get('id'))
        db_session = DBSession()

        result = "OK"
        message = ''

        spider = db_session.query(Spider).get(spider_id)

        if status not in SPIDER_ERROR_STATUSES:
            result = 'ERROR'
            message = 'Wrong error status'
        elif not spider:
            result = 'ERROR'
            message = 'Wrong spider id'
        else:
            spider_error = spider.error
            if status == 'fixed' and (not spider_error or (spider_error and spider_error.status == 'fixed')):
                spider_error = db_session.query(SpiderError)\
                    .filter(SpiderError.spider_id == spider.id,
                            SpiderError.status != 'fixed').limit(1).first()
                if not spider_error:
                    result = 'ERROR'
                    message = 'Spider don\'t have errors'
            elif not spider_error or (spider_error and spider_error.status == 'fixed'):
                spider_error = SpiderError()
                spider_error.spider_id = spider.id

            if spider_error and result == 'OK':

                spider_error.status = status

                if status == 'real':
                    if not spider_error.time_added:
                        spider_error.time_added = datetime.now()
                    spider_error.error_type = request.POST.get('error_type', '')
                    spider_error.error_desc = request.POST.get('error_desc', '')
                elif status == 'fixed':
                    spider_error.time_fixed = datetime.now()
                    # Remove Delisted Duplicates errors
                    db_session.query(DelistedDuplicateError)\
                        .filter(DelistedDuplicateError.website_id == spider.website_id,
                                DelistedDuplicateError.fixed != True)\
                        .delete()

                db_session.add(spider_error)

                if status == 'real':
                    # Daily errors
                    day_errors = db_session.query(DailyErrors).filter(DailyErrors.date == date.today()).first()
                    if day_errors:
                        day_errors.real += 1
                        if day_errors.possible > 0:
                            day_errors.possible -= 1
                    else:
                        day_errors = DailyErrors(date=date.today())
                        day_errors.real = 1
                        db_session.add(day_errors)

                if hasattr(request, 'user'):
                    user_activity = UserLog()
                    user_activity.username = request.user.username
                    user_activity.name = request.user.name
                    user_activity.spider_id = spider.id
                    if status == 'fixed':
                        user_activity.activity = 'Marked as fixed'
                    elif status == 'real':
                        user_activity.activity = 'Marked as real error'

                    error_type = spider_error.error_type
                    if error_type:
                        error_type = ERROR_TYPES_DICT[error_type]
                        if spider_error.error_desc:
                            error_type += ': ' + spider_error.error_desc
                        user_activity.activity += ' (%s)' % error_type
                    user_activity.date_time = datetime.now()
                    db_session.add(user_activity)

        output = {'status': result}
        if message:
            output['message'] = message
        if result == 'OK' and spider.error and spider.error.error_type:
            if spider.error.error_desc:
                output['error_type'] = spider.error.error_desc
            else:
                output['error_type'] = ERROR_TYPES_DICT[spider.error.error_type]
            output['error_type_value'] = spider.error.error_type

        return output
    else:
        return dict()

@view_config(route_name='save_spider_error_assignment', renderer='json', permission='administration')
def save_spider_error_assignment(request):
    if request.method == 'POST':
        assigned = request.POST.get('assign_to', None)
        spider_id = int(request.POST.get('id'))
        db_session = DBSession()

        message = ''

        spider = db_session.query(Spider).get(spider_id)

        if not spider:
            result = 'ERROR'
            message = 'Wrong spider id'
        elif not spider.error:
            result = 'ERROR'
            message = 'Spider does not have error'
        else:
            spider_error = spider.error
            developer = db_session.query(Developer).get(int(assigned))
            spider_error.assigned_to_id = developer.id

            db_session.add(spider_error)

            if hasattr(request, 'user'):
                user_activity = UserLog()
                user_activity.username = request.user.username
                user_activity.name = request.user.name
                user_activity.spider_id = spider.id
                user_activity.activity = 'Assigned %s' % developer.name
                user_activity.date_time = datetime.now()

                db_session.add(user_activity)

            result = "OK"

        output = {'status': result}
        if message:
            output['message'] = message

        return output
    else:
        return dict()

@view_config(route_name='assembla_authorization', permission='maintenance')
def assembla_authorization(request):
    if 'spider_name' in request.GET:
        request.session['assembla'] = {'spider_name': request.GET['spider_name']}
    else:
        request.session['assembla'] = {}

    assembla_login_url = assembla.get_login_url(request)
    return HTTPFound(assembla_login_url)

@view_config(route_name='assembla_callback', permission='maintenance')
def assembla_callback(request):
    if 'code' in request.params:
        code = request.params['code']
        access_token = assembla.authorize(request, code)

        if not access_token:
            # TODO: redirect to error page
            url = request.route_url(
                'list_all_spiders',
                _query={'errors': 'real'}
            )
            return HTTPFound(url)

        if 'spider_name' in request.session['assembla']:
            url = request.route_url(
                'list_all_spiders',
                _query={'errors': 'real'},
                _anchor='assign_to_assembla+' + request.session['assembla']['spider_name']
            )

            return HTTPFound(url)

    return HTTPFound(request.route_url('home'))

@view_config(route_name='assembla_ticket_submit', renderer="json", permission='administration')
def assembla_ticket_submit(request):
    form = Form(request, schema=AssemblaTicketSchema,
                defaults={'enabled': True})

    if form.validate():
        db_session = DBSession()
        spider = db_session.query(Spider).filter(Spider.id == form.data['id']).first()
        if not spider:
            return {
                "status": "error",
                "message": "spider does not exist"
            }
        developer = db_session.query(Developer).get(int(form.data['assign_to']))
        ticket_id = assembla.create_ticket_for_spider(request, form.data['summary'], form.data['description'], developer.assembla_id)
        if ticket_id:
            # upload spider source code
            if form.data['upload_source_file']:
                spider_source = get_spider_source_file(spider.account.name, spider.name)
                if spider_source:
                    document_id = assembla.ticket_add_attachment(request, ticket_id, spider_source, "original source")
                    if not document_id:
                        return {
                            "status": "error",
                            "message": "error uploading spider source code"
                        }

            if not spider.error or (spider.error and spider.error.status == 'fixed'):
                spider.error = SpiderError()
                spider.error.status = 'real'
                db_session.add(spider.error)
            spider_error = spider.error

            spider_error.assigned_to_id = developer.id
            spider_error.assembla_ticket_id = ticket_id

            db_session.add(spider_error)

            if hasattr(request, 'user'):
                user_activity = UserLog()
                user_activity.username = request.user.username
                user_activity.name = request.user.name
                user_activity.spider_id = spider.id
                user_activity.activity = 'Assigned %s' % developer.name
                user_activity.date_time = datetime.now()
                db_session.add(user_activity)

            return {
                "status": "ok",
                "assigned_to": spider_error.assigned_to_id,
                "assigned_to_name": developer.name,
                "ticket_id": spider_error.assembla_ticket_id
            }
        else:
            return {
                "status": "error",
                "message": "error while creating ticket"
            }

    else:
        return {
            "status": "error",
            "message": "form is not valid"
        }

@view_config(route_name="assembla_ticket_get", renderer="json", permission='maintenance')
def assembla_ticket_get(request):
    if not 'id' in request.params:
        return {
            "status": "error",
            "message": "necessary parameter is not set"
        }
    db_session = DBSession()
    spider = db_session.query(Spider).filter(Spider.id == request.params['id']).first()
    if not spider:
        return {
            "status": "error",
            "message": "spider does not exist"
        }

    assembla_ticket_id = spider.error.assembla_ticket_id
    if not assembla_ticket_id:
        return {
            "status": "error",
            "message": "spider does not have ticket assigned"
        }

    assembla_ticket = assembla.get_ticket(request, assembla_ticket_id)
    if not assembla_ticket:
        return {
            "status": "error",
            "message": "invalid ticket id"
        }

    assembla_user = assembla.get_user(request, assembla_ticket['assigned_to_id'])
    if not assembla_user:
        assembla_user = {'name': 'Not assigned'}

    return {
        'summary': assembla_ticket['summary'],
        'description': assembla_ticket['description'],
        'assigned_to': assembla_user['name'],
        'url': assembla_ticket['url']
    }

@view_config(route_name="upload_spider_source", renderer="json", permission='administration')
def upload_spider_source(request):
    spider_id = request.matchdict['spider_id']
    if not 'source_file' in request.params:
        return {
            "status": "error",
            "message": "necessary parameter is not set"
        }
    # save uploaded file to temp account
    clear_temp_spider()
    try:
        # get spider
        db_session = DBSession()
        spider = db_session.query(Spider).filter(Spider.id == spider_id).first()
        if not spider:
            return {
                "status": "error",
                "message": "spider does not exist"
            }

        save_uploaded_file(request.params['source_file'], TEMP_SPIDER_PATH)
        # validate spider
        if not validate_spider(TEMP_SPIDER_PATH):
            clear_temp_spider()
            return {
                'status': 'error',
                'message': 'validation failed'
            }

        # get spider file name
        spider_path = get_spider_source_file(spider.account.name, spider.name)
        shutil.move(TEMP_SPIDER_PATH, spider_path)
        clear_temp_spider()
        # TODO: commit changes to repo
        return {
            'status': 'ok'
        }
    except:
        clear_temp_spider()

@view_config(route_name='additional_changes', renderer='additional_changes.mako', permission='maintenance')
def additional_changes(request):
    crawl_id = request.matchdict['crawl_id']
    db_session = DBSession()
    crawl = db_session.query(Crawl).get(crawl_id)

    res = []

    filename, file_format = get_crawl_additional_changes_file(crawl.id, DATA_DIR)

    if filename:
        res = _get_additional_changes(filename, file_format)
    return {'products': res, 'crawl': crawl}

@view_config(route_name='additional_changes_paged', renderer='additional_changes.mako', permission='maintenance')
def additional_changes_paged(request):
    crawl_id = request.matchdict['crawl_id']
    db_session = DBSession()
    crawl = db_session.query(Crawl).get(crawl_id)

    if not crawl:
        return HTTPFound('/productspiders')

    per_page = 100

    page = int(request.GET.get('page', 1))
    start = (page - 1) * per_page

    end = start + per_page

    pages_count = (crawl.additional_changes_count / per_page) + 1

    res = []

    filename, file_format = get_crawl_additional_changes_file(crawl.id, DATA_DIR)

    if filename:
        res = _get_additional_changes(filename, file_format, start, end)

    return {'products': res, 'crawl': crawl, 'page': page, 'pages_count': pages_count}

@view_config(route_name='get_websites_real_errors', renderer='json', permission=Everyone)
def get_websites_real_errors(request):
    system_name = request.GET.get('system', '')
    db_session = DBSession()
    upload_dst = db_session.query(UploadDestination).filter(UploadDestination.name == system_name).first()
    if not upload_dst:
        return {}

    account_ids = [a.id for a in upload_dst.accounts]
    spiders = db_session.query(Spider).join(SpiderError).filter(and_(Spider.account_id.in_(account_ids),
                                                                     SpiderError.status == 'real')).all()

    spiders_possible = db_session.query(Spider).join(Crawl).filter(and_(Spider.account_id.in_(account_ids),
                                                                        Crawl.status == 'errors_found')).all()
    for spider in spiders_possible:
        last_crawl = db_session.query(Crawl).filter(Crawl.spider_id == spider.id).order_by(desc(Crawl.crawl_date),
                                                                                           desc(Crawl.id)).first()
        if last_crawl and last_crawl.status == 'errors_found':
            d = (datetime.now() - last_crawl.end_time).total_seconds()
            if ((d / 60) / 60) > 24:
                spiders.append(spider)

    return {'websites': list(set([s.website_id for s in spiders]))}

@view_config(route_name='get_priority_spiders', renderer='json', permission=Everyone)
def get_priority_spiders(request):
    db_session = DBSession()
    spiders = db_session.query(Spider).filter(Spider.priority_possible_errors == True)
    res = []
    for s in spiders:
        res.append(s.website_id)

    return res


@view_config(route_name='get_website_crawl_data', renderer='json', permission=Everyone)
def get_website_crawl_data(request):
    system_name = request.GET.get('system', '')
    website_id = request.GET.get('website_id', '')
    crawl_date = request.GET.get('crawl_date', datetime.today())
    if system_name == '':
        raise HTTPBadRequest("No system argument")
    if website_id == '':
        raise HTTPBadRequest("No website_id argument")
    if isinstance(crawl_date, basestring):
        try:
            crawl_date = datetime.strptime(crawl_date, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPBadRequest("Error converting date '%s'. Please use format: YYYY-mm-dd" % crawl_date)
    db_session = DBSession()
    upload_dst = db_session.query(UploadDestination).filter(UploadDestination.name == system_name).first()
    if not upload_dst:
        raise HTTPBadRequest("Bad system name")
    spider = db_session.query(Spider).filter(Spider.website_id == website_id).first()
    if spider:
        crawls = db_session.query(Crawl).filter(Crawl.spider_id == spider.id,
                                                Crawl.crawl_date >= crawl_date) \
                                        .order_by(Crawl.id.asc()).all()
        res = []
        for crawl in crawls:
            time_taken = ''
            if crawl.start_time and crawl.end_time:
                time_taken = str(crawl.end_time - crawl.start_time).split('.')[0]
            crawl_date = crawl.crawl_date.strftime('%Y-%m-%d %H:%M') if crawl.crawl_date is not None else ''
            crawl_start = crawl.start_time.strftime('%Y-%m-%d %H:%M') if crawl.start_time is not None else ''
            crawl_end = crawl.end_time.strftime('%Y-%m-%d %H:%M') if crawl.end_time is not None else ''
            res.append({'crawl_date': crawl_date,
                        'crawl_start': crawl_start,
                        'crawl_end': crawl_end,
                        'time_taken': time_taken, 'status': crawl.status})
        return res
    else:
        raise HTTPBadRequest("Invalid website_id argument")


@view_config(route_name='get_website_last_crawl_date', renderer='json', permission=Everyone)
def get_website_last_crawl_date(request):
    system_name = request.GET.get('system', '')
    website_id = request.GET.get('website_id', '')
    if system_name == '':
        raise HTTPBadRequest("No system argument")
    if website_id == '':
        raise HTTPBadRequest("No website_id argument")
    db_session = DBSession()
    upload_dst = db_session.query(UploadDestination).filter(UploadDestination.name == system_name).first()
    if not upload_dst:
        raise HTTPBadRequest("Bad system name")

    account_ids = [a.id for a in upload_dst.accounts]
    spider_q = db_session.query(Spider)\
        .filter(Spider.account_id.in_(account_ids))\
        .filter(Spider.website_id == website_id)
    if spider_q.count() != 1:
        raise HTTPNotFound("Spider not found")
    spider = spider_q.one()

    crawl = db_session.query(Crawl)\
        .filter(Crawl.spider_id == spider.id)\
        .order_by(desc(Crawl.crawl_date), desc(Crawl.id))\
        .first()
    if not crawl:
        return HTTPNotFound("Crawl given spider not found!")

    return {'id': crawl.id, 'date': crawl.crawl_date.strftime("%Y-%m-%d"), 'products_count': crawl.products_count}

@view_config(route_name='get_website_metadata_status', renderer='json', permission=Everyone)
def get_website_metadata_status(request):
    system_name = request.GET.get('system', '')
    website_id = request.GET.get('website_id', '')
    if system_name == '':
        raise HTTPBadRequest("No system argument")
    if website_id == '':
        raise HTTPBadRequest("No website_id argument")

    db_session = DBSession()

    upload_dst = db_session.query(UploadDestination).filter(UploadDestination.name == system_name).first()
    if not upload_dst:
        raise HTTPBadRequest("Bad system name")

    account_ids = [a.id for a in upload_dst.accounts]
    spider_q = db_session.query(Spider)\
        .filter(Spider.account_id.in_(account_ids))\
        .filter(Spider.website_id == website_id)
    if spider_q.count() != 1:
        raise HTTPNotFound("Spider not found")
    spider = spider_q.one()

    res = {
        'status': spider.enable_metadata
    }

    return res

@view_config(route_name='get_website_crawl_status', renderer='json', permission=Everyone)
def get_website_crawl_status(request):
    system_name = request.GET.get('system', '')
    website_id = request.GET.get('website_id', '')
    crawl_date = request.GET.get('crawl_date', date.today())
    if system_name == '':
        raise HTTPBadRequest("No system argument")
    if website_id == '':
        raise HTTPBadRequest("No website_id argument")
    if isinstance(crawl_date, basestring):
        try:
            crawl_date = datetime.strptime(crawl_date, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPBadRequest("Error converting date '%s'. Please use format: YYYY-mm-dd" % crawl_date)
    db_session = DBSession()
    upload_dst = db_session.query(UploadDestination).filter(UploadDestination.name == system_name).first()
    if not upload_dst:
        raise HTTPBadRequest("Bad system name")

    account_ids = [a.id for a in upload_dst.accounts]
    spider_q = db_session.query(Spider)\
        .filter(Spider.account_id.in_(account_ids))\
        .filter(Spider.website_id == website_id)
    if spider_q.count() != 1:
        raise HTTPNotFound("Spider not found")
    spider = spider_q.one()

    crawl_q = db_session.query(Crawl).filter(Crawl.spider_id == spider.id).filter(Crawl.crawl_date == crawl_date)
    if crawl_q.count() > 1:
        crawl_q2 = crawl_q.filter(Crawl.status == 'upload_finished')
        if crawl_q2.count() > 1:
            crawl_q2 = crawl_q2.order_by(desc(Crawl.id))
            crawl = crawl_q2.first()
            crawl_status = crawl.status
            count = crawl_q2.count()
            crawl_ids = [x.id for x in crawl_q2]
        elif crawl_q2.count() == 1:
            crawl = crawl_q2.one()
            crawl_status = crawl.status
            crawl_ids = [crawl.id]
            count = 1
        else:
            crawl_q = crawl_q.order_by(desc(Crawl.id))
            crawl = crawl_q.first()
            crawl_status = crawl.status
            crawl_ids = [crawl.id]
            count = 1
    elif crawl_q.count() == 1:
        crawl = crawl_q.one()
        crawl_status = crawl.status
        crawl_ids = [crawl.id]
        count = 1
    else:
        return HTTPNotFound("Crawl for given date and given spider not found!")

    return {'status': crawl_status, 'count': count, 'ids': crawl_ids}

@view_config(route_name='get_website_crawl_results', renderer='json', permission=Everyone)
def get_website_crawl_results(request):
    crawl_id = request.GET.get('crawl_id', '')
    db_session = DBSession()
    crawl = db_session.query(Crawl).get(crawl_id)
    if not crawl:
        return HTTPNotFound("Crawl for given date and given spider not found!")

    spider = db_session.query(Spider).get(crawl.spider_id)

    filename = '%s_products.csv' % crawl.id
    filepath = os.path.join(DATA_DIR, filename)

    r = FileResponse(filepath, request=request, content_type='text/csv')
    r.content_disposition = 'attachment; filename=%s_%s.csv' % (spider.website_id, crawl.id)

    return r

@view_config(route_name='get_website_crawl_metadata_results', permission=Everyone)
def get_crawl_metadata_results(request):
    crawl_id = request.GET.get('crawl_id', '')
    db_session = DBSession()
    crawl = db_session.query(Crawl).get(crawl_id)
    if not crawl:
        return HTTPNotFound("Crawl for given date and given spider not found!")

    filename, file_format = get_crawl_meta_file(crawl.id, DATA_DIR)

    if filename:
        res = _get_metadata_simple(filename, file_format)

        return Response(json.dumps({'products': res}))

@view_config(route_name='get_website_crawl_metadata_results_jsonl', permission=Everyone)
def get_crawl_metadata_results_jsonl(request):
    crawl_id = request.GET.get('crawl_id', '')
    db_session = DBSession()
    crawl = db_session.query(Crawl).get(crawl_id)
    if not crawl:
        return HTTPNotFound("Crawl for given date and given spider not found!")

    spider = db_session.query(Spider).get(crawl.spider_id)

    filepath, file_format = get_crawl_meta_file(crawl.id, DATA_DIR)

    if filepath:
        if file_format == 'json-lines':
            r = FileResponse(filepath, request=request, content_type='text/jsonl')
            r.content_disposition = 'attachment; filename=%s_%s.jsonl' % (spider.website_id, crawl.id)

            return r
        else:
            res = _get_metadata_simple(filepath, file_format)

            output = "\n".join(map(json.dumps, res))

            return Response(output)


def days_hours_minutes(td):
    return td.days, td.seconds // 3600, (td.seconds // 60) % 60

@view_config(route_name='get_account_last_updated', renderer='json', permission=Everyone)
def get_account_last_updated(request):
    member_id = request.GET.get('account_id', '')
    missing_days = int(request.GET.get('days', ''))

    db_session = DBSession()

    sites_not_uploaded_list = []

    account_db = db_session.query(Account)\
        .filter(Account.member_id == int(member_id)).first()
    if account_db:
        spiders = db_session.query(Spider)\
            .filter(Spider.account_id == int(account_db.id),
                    Spider.enabled == True)

        for spider in spiders:

            successful_crawls = db_session.query(Crawl)\
                .filter(Crawl.spider_id == spider.id,
                        Crawl.status == 'upload_finished')\
                .order_by(Crawl.crawl_date.asc(),
                          Crawl.id.asc())

            last_date = None

            for last_successful_crawl in successful_crawls:
                if last_successful_crawl and last_date and last_successful_crawl.crawl_date:
                    days_taken = last_successful_crawl.crawl_date - last_date
                    days = days_taken.days - 1
                else:
                    days = None

                if days and days >= missing_days:

                    sites_not_uploaded_list.append({
                        'website_id': spider.website_id,
                        'spider_name': spider.name,
                        'last_uploaded': last_date.strftime('%d/%m/%Y'),
                        'uploaded': last_successful_crawl.crawl_date.strftime('%d/%m/%Y'),
                        'days': days,
                    })

                last_date = last_successful_crawl.crawl_date

    return {'data': sites_not_uploaded_list}

@view_config(route_name='create_local_spider', renderer='json', permission=Everyone)
def create_local_spider(request):
    db_session = DBSession()
    name = request.GET.get('name')
    account = request.GET.get('account')
    spider_id = request.GET.get('id')

    if not name or not account or not spider_id:
        return {'status': 'error', 'msg': 'Missing parameters'}

    if not valid_spider_name(name):
        return {'status': 'error', 'msg': 'Invalid spider name'}

    if not account_exists(account):
        return {'status': 'error', 'msg': 'Account does not exist'}

    if db_session.query(Spider).filter(Spider.name == name).first():
        return {'status': 'error', 'msg': 'Spider name already used'}


    create_spider_file(account, name, spider_id)

    return {'status': 'ok'}

@view_config(route_name='delete_local_spider', renderer='json', permission=Everyone)
def delete_local_spider(request):
    db_session = DBSession()
    name = request.GET.get('name')
    account = request.GET.get('account')

    if not name or not account:
        return {'status': 'error', 'msg': 'Missing parameters'}

    if not valid_spider_name(name):
        return {'status': 'error', 'msg': 'Invalid spider name'}

    if not account_exists(account):
        return {'status': 'error', 'msg': 'Account does not exist'}

    delete_spider(account, name)
    spider = db_session.query(Spider).filter(Spider.name == name).first()
    if spider:
        spider_errors = db_session.query(SpiderError).filter(SpiderError.spider_id == spider.id).all()
        for e in spider_errors:
            db_session.delete(e)

        crawls = db_session.query(Crawl).filter(Crawl.spider_id == spider.id).all()
        for c in crawls:
            db_session.delete(c)

        db_session.delete(spider)

    return {'status': 'ok'}

API_URL = 'http://%s.competitormonitor.com/api/create_website.json'
API_KEY = '3Df7mNg'
@view_config(route_name='setup_spider', renderer='json', permission=Everyone)
def setup_spider(request):
    db_session = DBSession()
    name = request.GET.get('name', '')
    website_name = request.GET.get('website_name', '')
    marketplace = request.GET.get('marketplace', '')
    default_identifier = request.GET.get('default_identifier', '')
    currency = request.GET.get('currency', '')
    member_id = request.GET.get('member_id')
    url = request.GET.get('url')

    if not name or not currency or not website_name or not member_id or not url:
        return {'status': 'error', 'msg': 'Missing parameters'}

    account = db_session.query(Account).filter(Account.member_id == member_id).first()
    if not account or not account.upload_destinations:
        return {'status': 'error', 'msg': 'Account not configured'}

    spider = db_session.query(Spider).filter(Spider.name == name).first()
    if spider:
        return {'status': 'error', 'msg': 'Spider already configured'}

    params = {'website_name': website_name, 'default_identifier': default_identifier or 'name',
              'member_id': member_id, 'marketplace': marketplace, 'currency': currency,
              'api_key': API_KEY, 'url': url}

    sys_domain = {'lego_system': 'lego', 'new_system': 'app'}
    dst = None
    for d in account.upload_destinations:
        if d.name in sys_domain:
            dst = d
            break

    if not dst:
        return {'status': 'error', 'msg': 'Account not configured to upload to a known system'}

    r = json.loads(urllib2.urlopen((API_URL % sys_domain[dst.name]) + '?' + urllib.urlencode(params)).read())

    if r['status'] == 'error':
        return r

    spider = Spider()
    spider.account_id = account.id
    spider.enabled = False
    spider.automatic_upload = True
    spider.name = name
    spider.start_hour = 0
    spider.upload_hour = 0
    spider.additional_changes_percentage_error = 10
    spider.additions_percentage_error = 10
    spider.deletions_percentage_error = 10
    spider.max_price_change_percentage = 80
    spider.price_updates_percentage_error = 50
    spider.update_percentage_error = 80
    spider.website_id = int(r['id'])
    db_session.add(spider)

    return {'status': 'ok'}

@view_config(route_name='setup_spider2', renderer='json', permission=Everyone)
def setup_spider2(request):
    db_session = DBSession()
    name = request.params.get('name', '')
    website_name = request.params.get('website_name', '')
    marketplace = request.params.get('marketplace', '')
    default_identifier = request.params.get('default_identifier', '')
    currency = request.params.get('currency', '')
    member_id = request.params.get('member_id')
    url = request.params.get('url')
    create_compmon_website = request.params.get('create_compmon_website', False)

    start_url = request.params.get('start_url')
    try:
        extractors = json.loads(request.params.get('extractors'))
    except ValueError:
        return {'status': 'error', 'msg': 'Invalid JSON for `extractors` field'}

    try:
        start_urls = json.loads(request.params.get('start_urls'))
    except ValueError:
        return {'status': 'error', 'msg': 'Invalid JSON for `starts_urls` field'}

    if not name or not member_id:
        return {'status': 'error', 'msg': 'Missing parameters for creating spider'}

    account = db_session.query(Account).filter(Account.member_id == member_id).first()
    if not account or not account.upload_destinations:
        return {'status': 'error', 'msg': 'Account not configured'}

    spider = db_session.query(Spider).filter(Spider.name == name).first()
    if spider:
        return {'status': 'error', 'msg': 'Spider already configured'}

    r = None
    if create_compmon_website:
        if not website_name or not currency or not url:
            return {'status': 'error', 'msg': 'Missing parameters for creating compmon object'}
        params = {'website_name': website_name, 'default_identifier': default_identifier or 'name',
                  'member_id': member_id, 'marketplace': marketplace, 'currency': currency,
                  'api_key': API_KEY, 'url': url}

        sys_domain = {'lego_system': 'lego', 'new_system': 'app'}
        dst = None
        for d in account.upload_destinations:
            if d.name in sys_domain:
                dst = d
                break

        if not dst:
            return {'status': 'error', 'msg': 'Account not configured to upload to a known system'}

        r = json.loads(urllib2.urlopen((API_URL % sys_domain[dst.name]) + '?' + urllib.urlencode(params)).read())

        if r['status'] == 'error':
            return r

    spider = Spider()
    spider.account_id = account.id
    spider.enabled = False
    spider.automatic_upload = True
    spider.name = name
    spider.start_hour = 0
    spider.upload_hour = 0
    spider.additional_changes_percentage_error = 10
    spider.additions_percentage_error = 10
    spider.deletions_percentage_error = 10
    spider.max_price_change_percentage = 80
    spider.price_updates_percentage_error = 50
    spider.update_percentage_error = 80
    spider.parse_method = 'Scrapely'
    if r:
        spider.website_id = int(r['id'])

    scrapely_spider_data = ScrapelySpiderData()
    scrapely_spider_data.start_url = start_url
    scrapely_spider_data.start_urls_json = json.dumps(start_urls)
    scrapely_spider_data.extractors = []

    for ex in extractors:
        scrapely_extractor = ScrapelySpiderExtractor()
        scrapely_extractor.type = ex['type']
        scrapely_extractor.templates_json = ex['templates_json']
        scrapely_extractor.fields_spec_json = json.dumps(ex['fields_spec_json']) \
            if isinstance(ex['fields_spec_json'], dict) else ex['fields_spec_json']

        scrapely_spider_data.extractors.append(scrapely_extractor)
    spider.scrapely_data = scrapely_spider_data
    db_session.add(scrapely_spider_data)
    db_session.add(spider)

    transaction.commit()

    spider = db_session.query(Spider).filter(Spider.name == name).one()
    account = db_session.query(Account).filter(Account.member_id == member_id).one()

    return {'status': 'ok', 'spider_id': spider.id, 'account_id': account.id}

@view_config(route_name='update_setuped_spider2', renderer='json', permission=Everyone)
def update_setuped_spider2(request):
    db_session = DBSession()
    spider_id = request.params.get('spider_id')

    start_url = request.params.get('start_url')
    try:
        extractors = json.loads(request.params.get('extractors'))
    except ValueError:
        return {'status': 'error', 'msg': 'Invalid JSON for `extractors` field'}

    try:
        start_urls = json.loads(request.params.get('start_urls'))
    except ValueError:
        return {'status': 'error', 'msg': 'Invalid JSON for `starts_urls` field'}

    spider = db_session.query(Spider).filter(Spider.id == spider_id).first()
    if not spider:
        return {'status': 'error', 'msg': 'Spider not found'}

    spider.parse_method = 'Scrapely'

    scrapely_spider_data = spider.scrapely_data
    scrapely_spider_data.start_url = start_url
    scrapely_spider_data.start_urls_json = json.dumps(start_urls)
    for ex in scrapely_spider_data.extractors:
        db_session.delete(ex)
    scrapely_spider_data.extractors = []

    for ex in extractors:
        scrapely_extractor = ScrapelySpiderExtractor()
        scrapely_extractor.type = ex['type']
        scrapely_extractor.templates_json = ex['templates_json']
        scrapely_extractor.fields_spec_json = json.dumps(ex['fields_spec_json']) \
            if isinstance(ex['fields_spec_json'], dict) else ex['fields_spec_json']

        scrapely_spider_data.extractors.append(scrapely_extractor)
    spider.scrapely_data = scrapely_spider_data
    db_session.add(scrapely_spider_data)
    db_session.add(spider)

    transaction.commit()

    spider = db_session.query(Spider).filter(Spider.id == spider_id).one()
    account = db_session.query(Account).filter(Account.id == spider.account_id).one()

    return {'status': 'ok', 'spider_id': spider.id, 'account_id': account.id}

@view_config(route_name='update_spider_status', renderer='json', permission=Everyone)
def update_spider_status(request):
    db_session = DBSession()
    name = request.GET.get('name', '')
    status = request.GET.get('status', '')

    if not name or not status:
        return {'status': 'error', 'msg': 'Missing parameters'}

    if status not in ['enabled', 'disabled']:
        return {'status': 'error', 'msg': 'Wrong status'}

    spider = db_session.query(Spider).filter(Spider.name == name).first()
    if not spider:
        return {'status': 'error', 'msg': 'spider not found'}

    spider.enabled = status == 'enabled'
    db_session.add(spider)

    return {'status': 'ok'}

@view_config(route_name='update_account_status', renderer='json', permission=Everyone)
def update_account_status(request):
    db_session = DBSession()
    account_id = request.GET.get('id', '')
    status = request.GET.get('status', '')

    if not account_id or not status:
        return {'status': 'error', 'msg': 'Missing parameters'}

    if status not in ['enabled', 'disabled']:
        return {'status': 'error', 'msg': 'Wrong status'}

    account = db_session.query(Account).filter(Account.member_id == account_id).first()
    if not account:
        return {'status': 'error', 'msg': 'spider not found'}

    account.enabled = status == 'enabled'
    db_session.add(account)

    return {'status': 'ok'}

@view_config(route_name='check_account_status', renderer='json', permission=Everyone)
def check_account_status(request):
    system_name = request.GET.get('system', '')
    member_id = request.GET.get('member_id', '')
    if system_name == '':
        raise HTTPBadRequest("No system argument")
    if member_id == '':
        raise HTTPBadRequest("No member_id argument")

    db_session = DBSession()
    upload_dst = db_session.query(UploadDestination).filter(UploadDestination.name == system_name).first()
    if not upload_dst:
        raise HTTPBadRequest("Bad system name")

    account_q = db_session.query(Account).filter(Account.member_id == member_id)
    if account_q.count() < 1:
        exists = False
        enabled = False
    else:
        exists = True
        account = account_q.first()
        enabled = account.enabled
    return {'exists': exists, 'enabled': enabled}

@view_config(route_name='check_website_status', renderer='json', permission=Everyone)
def check_website_status(request):
    system_name = request.GET.get('system', '')
    website_id = request.GET.get('website_id', '')
    if system_name == '':
        raise HTTPBadRequest("No system argument")
    if website_id == '':
        raise HTTPBadRequest("No website_id argument")

    db_session = DBSession()
    upload_dst = db_session.query(UploadDestination).filter(UploadDestination.name == system_name).first()
    if not upload_dst:
        raise HTTPBadRequest("Bad system name")

    spider_q = db_session.query(Spider).filter(Spider.website_id == website_id)
    if spider_q.count() < 1:
        exists = False
        enabled = False
        test = False
    else:
        exists = True
        spider = spider_q.first()
        enabled = spider.enabled
        test = spider.upload_testing_account

    return {'exists': exists, 'enabled': enabled, 'test': test}




@view_config(route_name='matching.get_accounts_json', permission=Everyone)
def get_accounts_json(request):
    db_session = DBSession()

    db_accounts = db_session.query(Account).all()

    accounts = []
    for account in db_accounts:
        dsts = []
        for dst in account.upload_destinations:
            dsts.append({
                'name': dst.name,
                'type': dst.type
                })

        accounts.append({
            'id': account.id,
            'name': account.name,
            'member_id': account.member_id,
            'enabled': account.enabled,
            'dsts': dsts
            })

    res = {'accounts': sorted(accounts, key=lambda x: x['name'])}

    return Response(json.dumps(res))

@view_config(route_name='matching.get_spiders_json', permission=Everyone)
def get_spiders_json(request):
    db_session = DBSession()

    active = request.GET.get('active', None) == '1'

    spiders = []

    if active:
        spider_query = db_session.query(Spider)\
            .join(Account, Account.id == Spider.account_id)\
            .filter(Account.enabled == True)\
            .filter(Spider.enabled == True)
    else:
        spider_query = db_session.query(Spider)

    for spider in spider_query:
        item = {
            'id': spider.id,
            'account_id': spider.account_id,
            'enabled': spider.enabled,
            'website_id': spider.website_id
        }
        spiders.append(item)

    res = {'spiders': spiders}
    return Response(json.dumps(res))

@view_config(route_name='matching.get_spider_crawls_json', permission=Everyone)
def get_spider_crawls(request):
    db_session = DBSession()

    member_id = request.matchdict['member_id']

    account = db_session.query(Account).filter(Account.member_id == member_id).first()
    if not account:
        raise HTTPNotFound("Account with member id %s not found" % member_id)

    website_id = request.matchdict['website_id']

    spider = db_session.query(Spider)\
        .filter(Spider.website_id == website_id)\
        .filter(Spider.account_id == account.id).first()
    if not spider:
        raise HTTPNotFound("Spider with website id %s not found in account with member_id %s" % (website_id, member_id))

    crawls_db = db_session.query(Crawl)\
        .filter(Crawl.spider_id == spider.id)\
        .filter(Crawl.status == 'upload_finished')\
        .all()

    crawls = []

    for c in crawls_db:
        temp = {
            'id': c.id,
            'date': c.crawl_date.strftime("%Y-%m-%d"),
            'products_count': c.products_count,
            'changes_count': c.changes_count,
            'additions_count': c.additions_count,
            'deletions_count': c.deletions_count,
            'updates_count': c.updates_count,
            'additional_changes_count': c.additional_changes_count,
        }

        crawls.append(temp)

    return Response(json.dumps({
        'crawls': crawls
    }))

@view_config(route_name='matching.get_last_crawls_json', permission=Everyone)
def get_last_crawls_json(request):
    db_session = DBSession()
    max_crawl_id = db_session.query(func.max(Crawl.id).label('id')) \
                   .filter(Crawl.status == 'upload_finished') \
                   .group_by(Crawl.spider_id).subquery()


    crawls = []
    for crawl in db_session.query(Crawl).join((max_crawl_id, (Crawl.id == max_crawl_id.c.id))):
        item = {
            'id': crawl.id,
            'spider_id': crawl.spider_id,
            'crawl_date': crawl.crawl_date.isoformat(),
            'products_count': crawl.products_count
        }
        crawls.append(item)

    res = {'crawls': crawls}
    return Response(json.dumps(res))


@view_config(route_name='matching.get_crawl_results_csv', permission=Everyone)
def get_crawl_results(request):
    db_session = DBSession()
    crawl_id = request.matchdict['crawl_id']

    crawl = db_session.query(Crawl).get(crawl_id)
    if not crawl:
        raise HTTPNotFound("Crawl with id %s not found" % crawl_id)

    try:
        f = open(os.path.join(DATA_DIR, '%s_products.csv' % crawl.id))
    except IOError:
        raise HTTPNotFound("Results for crawl %s not found" % crawl_id)

    resp = Response(body_file=f)
    resp.content_type = 'text/csv'

    return resp

@view_config(route_name='matching.get_crawl_changes_csv', permission=Everyone)
def get_crawl_changes(request):
    db_session = DBSession()
    crawl_id = request.matchdict['crawl_id']

    crawl = db_session.query(Crawl).get(crawl_id)
    if not crawl:
        raise HTTPNotFound("Crawl with id %s not found" % crawl_id)

    try:
        f = open(os.path.join(DATA_DIR, '%s_changes_new.csv' % crawl.id))
    except IOError:
        raise HTTPNotFound("Changes for crawl %s not found" % crawl_id)

    resp = Response(body_file=f)
    resp.content_type = 'text/csv'

    return resp


@view_config(route_name='crawls_stats', renderer='crawls_stats.mako', permission='administration')
def crawls_stats(request):
    db_session = DBSession()
    spiders = db_session.query(Spider).join(Account).filter(and_(Spider.enabled == True, Account.enabled == True)).all()

    results = []
    for spider in spiders:
        last_crawl = db_session.query(Crawl).filter(and_(Crawl.spider_id == spider.id,
                                                    Crawl.start_time != None,
                                                    Crawl.end_time != None)).order_by(desc(Crawl.id)).first()
        if last_crawl:
            diff = last_crawl.end_time - last_crawl.start_time
            ppm = 0
            if diff.total_seconds() > 0:
                ppm = last_crawl.products_count / (diff.total_seconds() / 60)

            account = db_session.query(Account).get(spider.account_id)
            results.append({'account_name': account.name, 'name': spider.name, 'start_time': last_crawl.start_time,
                            'end_time': last_crawl.end_time, 'time_taken': diff,
                            'products_count': last_crawl.products_count,
                            'use_proxies': spider.use_proxies, 'use_tor': spider.use_tor,
                            'products_per_min': ppm})

    results.sort(key=lambda x: x['time_taken'], reverse=True)

    return {'spiders': results}

@view_config(route_name='list_proxy_lists', renderer='list_proxy_lists.mako', permission='administration')
def list_proxy_lists(request):
    db_session = DBSession()
    proxy_lists = db_session.query(ProxyList).all()

    return {'proxy_lists': proxy_lists}

@view_config(route_name='delete_proxy_list', permission='administration')
def delete_proxy_list(request):
    db_session = DBSession()
    proxy_list = db_session.query(ProxyList).get(request.GET.get('id'))
    if proxy_list:
        spiders = db_session.query(Spider).filter(Spider.proxy_list_id == proxy_list.id).all()
        for s in spiders:
            s.proxy_list_id = None
            db_session.add(s)
        db_session.delete(proxy_list)

    return HTTPFound(request.route_url('list_proxy_lists'))

@view_config(route_name='config_proxy_list', renderer='config_proxy_list.mako', permission='administration')
def config_proxy_list(request):
    db_session = DBSession()

    if request.GET.get('id') or request.POST.get('id'):
        proxy_id = request.GET.get('id') or request.POST.get('id')
        proxy_list = db_session.query(ProxyList).get(proxy_id)
    else:
        proxy_list = ProxyList()
        proxy_list.name = ''
        proxy_list.proxies = ''

    form = Form(request, schema=ProxyListSchema, obj=proxy_list)

    if form.validate():
        form.bind(proxy_list)

        db_session.add(proxy_list)

        return HTTPFound(request.route_url('list_proxy_lists'))

    return {'renderer': FormRenderer(form), 'proxy_list': proxy_list if proxy_list.id else None}


@view_config(route_name='list_deleted_products', renderer='list_deleted_products.mako', permission='deletions_management')
def list_deleted_products(request):
    db_session = DBSession()
    deleted_products = db_session.query(DeletionsReview).\
        filter(DeletionsReview.status == 'new').\
        order_by(desc(DeletionsReview.crawl_date)).\
        all()
    return {'deleted_products': deleted_products}


@view_config(route_name='deletion_review_bad_delete', renderer='json', permission='deletions_management')
def deletion_review_bad_delete(request):
    if request.method == 'POST':
        deletion_review_id = request.POST.get('deletion_review_id')
        db_session = DBSession()
        deletion_review = db_session.query(DeletionsReview).filter(DeletionsReview.id == deletion_review_id).first()
        if deletion_review:
            deletion_review.status = 'needs_fixing'
            deletion_review.found_date = datetime.now()
            db_session.add(deletion_review)
            return {'ok': 'OK!'}
    return {'error': 'ERROR!'}


@view_config(route_name='deletion_review_good_delete', renderer='json', permission='deletions_management')
def deletion_review_good_delete(request):
    if request.method == 'POST':
        deletion_review_id = request.POST.get('deletion_review_id')
        db_session = DBSession()
        deletion_review = db_session.query(DeletionsReview).filter(DeletionsReview.id == deletion_review_id).first()
        if deletion_review:
            db_session.delete(deletion_review)
            return {'ok': 'OK!'}
    return {'error': 'ERROR!'}


@view_config(route_name='deleted_products_errors', renderer='deleted_products_errors.mako', permission='administration')
def deleted_products_errors(request):
    db_session = DBSession()
    json_url = request.route_url("deleted_products_errors_json")
    if 'assembla' in request.session\
       and 'authorized' in request.session['assembla']\
       and request.session['assembla']['authorized']:
        assembla_authorized = True
        assembla_ticket_submit_url = request.route_url("assembla_deletions_ticket_submit")
        assembla_authorization_url = ""
    else:
        assembla_authorized = False
        assembla_ticket_submit_url = ""
        assembla_authorization_url = request.route_url('assembla_authorization')

    developers = [{'id': d.id, 'name': d.name, 'assembla_id': d.assembla_id} for d in db_session.query(Developer).all()]

    return dict(
        json_url=json_url,
        developers=json.dumps(developers),
        assembla_authorized=assembla_authorized,
        assembla_ticket_submit_url=assembla_ticket_submit_url,
        assembla_authorization_url=assembla_authorization_url
    )


@view_config(route_name='deleted_products_errors_json', permission='administration')
def deleted_products_errors_json(request):
    db_session = DBSession()
    query = db_session.query(DeletionsReview.found_date,
                             DeletionsReview.crawl_date,
                             DeletionsReview.account_name,
                             DeletionsReview.site,
                             DeletionsReview.spider_id,
                             DeletionsReview.crawl_id,
                             DeletionsReview.assigned_to,
                             DeletionsReview.assembla_ticket_id,
                             func.sum(cast(DeletionsReview.matched, Integer)).label('matched_count'),
                             func.count('*').label('total'))
    query = query.filter(DeletionsReview.status == 'needs_fixing')
    query = query.group_by(DeletionsReview.found_date,
                           DeletionsReview.crawl_date,
                           DeletionsReview.spider_id,
                           DeletionsReview.account_name,
                           DeletionsReview.site,
                           DeletionsReview.crawl_id,
                           DeletionsReview.assigned_to,
                           DeletionsReview.assembla_ticket_id)
    items = query.all()

    jlist = []
    for item in items:
        jitem = dict()
        jitem['found_date'] = item.found_date.isoformat()
        jitem['crawl_date'] = item.crawl_date.isoformat()
        jitem['account_name'] = item.account_name
        jitem['site'] = item.site
        jitem['spider_id'] = item.spider_id
        jitem['crawl_id'] = item.crawl_id
        jitem['assigned_to'] = item.assigned_to
        jitem['assembla_ticket_id'] = item.assembla_ticket_id
        jitem['matched_count'] = item.matched_count
        jitem['total'] = item.total
        jitem['unmatched_count'] = item.total - item.matched_count
        jitem['products_url'] = request.route_url('show_deleted_products', _query={'crawl_id': item.crawl_id})
        jitem['change_error_status_url'] = request.route_url('deleted_products_mark_as_fixed',
                                                         _query={'crawl_id': item.crawl_id})
        jitem['save_error_assignment_url'] = request.route_url('save_deletions_error_assignment')
        jitem['assembla_authorization_url'] = request.route_url('assembla_authorization', _query={'spider_name': item.site})
        jitem['assembla_ticket_url'] = request.route_url('assembla_deletions_ticket_get', _query={'id': item.crawl_id})
        jitem['upload_spider_source'] = request.route_url('upload_spider_source', spider_id=item.crawl_id)
        jlist.append(jitem)

    json_items = json.dumps(jlist)

    return Response(json_items)


@view_config(route_name='save_deletions_error_assignment', renderer='json', permission='administration')
def save_deletions_error_assignment(request):
    if request.method == 'POST':
        assigned = request.POST.get('assigned', None)
        crawl_id = int(request.POST.get('id'))
        db_session = DBSession()
        db_session.query(DeletionsReview).filter(DeletionsReview.crawl_id == crawl_id).update({'assigned_to': assigned})
        return {'status': "OK"}
    else:
        return dict()


@view_config(route_name="assembla_deletions_ticket_get", renderer="json", permission='maintenance')
def assembla_deletions_ticket_get(request):
    if not 'id' in request.params:
        return {
            "status": "error",
            "message": "necessary parameter is not set"
        }
    db_session = DBSession()
    dr = db_session.query(DeletionsReview).filter(DeletionsReview.crawl_id == request.params['id']).first()
    if not dr:
        return {
            "status": "error",
            "message": "Deletion issue does not exist"
        }

    assembla_ticket_id = DeletionsReview.assembla_ticket_id
    if not assembla_ticket_id:
        return {
            "status": "error",
            "message": "Deletion issue does not have ticket assigned"
        }

    assembla_ticket = assembla.get_ticket(request, assembla_ticket_id)
    if not assembla_ticket:
        return {
            "status": "error",
            "message": "invalid ticket id"
        }

    assembla_user = assembla.get_user(request, assembla_ticket['assigned_to_id'])
    if not assembla_user:
        assembla_user = {'name': 'Not assigned'}

    return {
        'summary': assembla_ticket['summary'],
        'description': assembla_ticket['description'],
        'assigned_to': assembla_user['name'],
        'url': assembla_ticket['url']
    }


@view_config(route_name='assembla_deletions_ticket_submit', renderer="json", permission='administration')
def assembla_deletion_ticket_submit(request):
    form = Form(request, schema=AssemblaTicketSchema,
                defaults={'enabled': True})

    if form.validate():
        db_session = DBSession()
        dr = db_session.query(DeletionsReview).filter(DeletionsReview.crawl_id == form.data['id']).first()
        if not dr:
            return {
                "status": "error",
                "message": "Deletion issue does not exist"
            }
        ticket_id = assembla.create_ticket_for_spider(request,
                                                      form.data['summary'],
                                                      form.data['description'],
                                                      form.data['assign_to'])
        if ticket_id:
            # upload spider source code
            if form.data['upload_source_file']:
                spider_source = get_spider_source_file(dr.account_name, dr.site)
                if spider_source:
                    document_id = assembla.ticket_add_attachment(request, ticket_id, spider_source, "original source")
                    if not document_id:
                        return {
                            "status": "error",
                            "message": "error uploading spider source code"
                        }

            assembla_user_id = form.data['assign_to']
            assembla_user = assembla.get_user(request, assembla_user_id)
            db_session.query(DeletionsReview).filter(DeletionsReview.crawl_id == form.data['id']).\
                update({'assigned_to': assembla_user['name'],
                        'assembla_ticket_id': ticket_id})

            return {
                "status": "ok",
                "assigned_to": assembla_user['name'],
                "ticket_id": ticket_id
            }
        else:
            return {
                "status": "error",
                "message": "error while creating ticket"
            }

    else:
        return {
            "status": "error",
            "message": "form is not valid"
        }


@view_config(route_name='deleted_products_mark_as_fixed', renderer='json', permission='administration')
def deleted_products_mark_as_fixed(request):
    if request.method == 'POST':
        crawl_id = request.POST.get('crawl_id')
        db_session = DBSession()
        db_session.query(DeletionsReview).filter(DeletionsReview.crawl_id == crawl_id).delete()
        return {'ok': 'OK!'}
    return {'error': 'ERROR!'}


@view_config(route_name='show_deleted_products', renderer='show_deleted_products.mako', permission='administration')
def show_deleted_products(request):
    db_session = DBSession()
    crawl_id = request.params.get('crawl_id')
    deleted_products = db_session.query(DeletionsReview)\
        .filter(DeletionsReview.crawl_id == crawl_id)\
        .filter(DeletionsReview.status == 'needs_fixing')\
        .all()
    return {'deleted_products': deleted_products}

# Worker server
@view_config(route_name='list_worker_servers', renderer='list_worker_servers.mako', permission='administration')
def list_worker_servers(request):
    db_session = DBSession()
    worker_servers = db_session.query(WorkerServer).all()

    return {'worker_servers': worker_servers}

@view_config(route_name='config_worker_server', renderer='config_worker_server.mako', permission='administration')
def config_worker_server(request):
    db_session = DBSession()

    if request.GET.get('id') or request.POST.get('id'):
        worker_server_id = request.GET.get('id') or request.POST.get('id')
        worker_server = db_session.query(WorkerServer).get(worker_server_id)
    else:
        worker_server = WorkerServer()
        worker_server.name = ''
        worker_server.host = ''
        worker_server.user = ''
        worker_server.password = ''
        worker_server.port = 22
        worker_server.enabled = True

    form = Form(request, schema=WorkerServerSchema, obj=worker_server)

    if form.validate():
        form.bind(worker_server)

        db_session.add(worker_server)

        return HTTPFound(request.route_url('list_worker_servers'))

    return {'renderer': FormRenderer(form), 'worker_server': worker_server if worker_server.id else None}


@view_config(route_name='delete_worker_server', permission='administration')
def delete_worker_server(request):
    db_session = DBSession()
    worker_server = db_session.query(WorkerServer).get(request.GET.get('id'))
    if worker_server:
        spiders = db_session.query(Spider).filter(Spider.worker_server_id == worker_server.id).all()
        for s in spiders:
            s.worker_server_id = None
            db_session.add(s)

        db_session.delete(worker_server)

    return HTTPFound(request.route_url('list_worker_servers'))


@view_config(route_name='hide_disabled_site', renderer='json', permission='administration')
def hide_disabled_site(request):
    if request.method == 'POST':
        spider_id = int(request.POST.get('id'))
        db_session = DBSession()
        spider = db_session.query(Spider).get(spider_id)
        spider.hide_disabled = True
        db_session.add(spider)
        return {'status': "OK"}
    else:
        return {}


@view_config(route_name='show_disabled_site', renderer='json', permission='administration')
def show_disabled_site(request):
    if request.method == 'POST':
        spider_id = int(request.POST.get('id'))
        db_session = DBSession()
        spider = db_session.query(Spider).get(spider_id)
        spider.hide_disabled = False
        db_session.add(spider)
        return {'status': "OK"}
    else:
        return {}


@view_config(route_name='list_all_disabled_sites', renderer='json', permission='administration')
def list_all_disabled_sites(request):
    def format_date(x):
        x['last_updated'] = x['last_updated'].strftime('%d/%m/%Y') if x['last_updated'] else ''
        return x

    db_session = DBSession()

    disabled_sites = []

    for site in _get_disabled_sites(True):
        last_crawl = db_session.query(Crawl)\
                .filter(Crawl.spider_id == site.id)\
                .order_by(desc(Crawl.crawl_date)).first()
        if last_crawl:
            if last_crawl.end_time:
                last_updated = last_crawl.end_time.date()
            elif last_crawl.start_time:
                last_updated = last_crawl.start_time.date()
            else:
                last_updated = last_crawl.crawl_date
        else:
            last_updated = None
        disabled_sites.append({'account_name': site.account.name,
                               'site_name': site.name,
                               'site_id': site.id,
                               'auto_upload': site.automatic_upload,
                               'enabled': site.enabled,
                               'last_updated': last_updated,
                               'hidden': site.hide_disabled,
                               })

    disabled_sites = map(format_date, sorted(disabled_sites, key=lambda x: x['last_updated'] if x['last_updated'] else date.today()))

    return disabled_sites

@view_config(route_name='list_daily_errors', renderer='json', permission='administration')
def list_daily_errors(request):
    from_ = datetime.strptime(request.matchdict['from'], '%d/%m/%Y').date()
    to = datetime.strptime(request.matchdict['to'], '%d/%m/%Y').date()

    if from_ <= to:
        db_session = DBSession()

        stats = db_session.query(DailyErrors).filter(DailyErrors.date.between(from_, to)).order_by(DailyErrors.date)
        total = stats.count()

        days = []
        possible = []
        real = []

        current_day = from_
        current_stat = 0

        while current_day <= to:
            days.append(current_day.strftime('%b %d'))
            if current_stat < total and current_day == stats[current_stat].date:
                possible.append(stats[current_stat].possible)
                real.append(stats[current_stat].real)
                current_stat += 1
            else:
                possible.append(0)
                real.append(0)
            current_day += timedelta(days=1)

        return {'days': days, 'possible': possible, 'real': real}
    else:
        return {'days': [], 'possible': [], 'real': []}

@view_config(route_name='list_total_real_errors', renderer='json', permission='administration')
def list_total_real_errors(request):
    start_date = datetime(day=3, month=10, year=2014)  # From here the data will be valid
    tomorrow_date = date.today() + timedelta(days=1)
    finish_date = datetime(day=tomorrow_date.day, month=tomorrow_date.month, year=tomorrow_date.year)
    from_ = datetime.strptime(request.matchdict['from'], '%d/%m/%Y')
    to = datetime.strptime(request.matchdict['to'], '%d/%m/%Y')

    if from_ <= to and to >= start_date:
        db_session = DBSession()

        days = []
        real = []
        current_day = from_

        while current_day <= to:
            days.append(current_day.strftime('%b %d'))
            next_day = current_day + timedelta(days=1)
            if current_day >= start_date and current_day < finish_date:
                total_errors = db_session.query(SpiderError)\
                    .filter(SpiderError.time_added < next_day,
                            or_(SpiderError.time_fixed >= current_day,
                                SpiderError.time_fixed == None))\
                    .count()
            else:
                total_errors = 0
            real.append(total_errors)

            current_day = next_day

        return {'days': days, 'real': real}
    else:
        return {'days': [], 'real': []}

# Additional fields groups
@view_config(route_name='list_additional_fields_groups', renderer='list_additional_fields_groups.mako', permission='administration')
def list_additional_fields_groups(request):
    db_session = DBSession()
    additional_fields_groups = db_session.query(AdditionalFieldsGroup).all()

    return {'additional_fields_groups': additional_fields_groups}

@view_config(route_name='config_additional_fields_group', renderer='config_additional_fields_group.mako', permission='administration')
def config_additional_fields_group(request):
    db_session = DBSession()

    if request.GET.get('id') or request.POST.get('id'):
        additional_fields_group_id = request.GET.get('id') or request.POST.get('id')
        additional_fields_group = db_session.query(AdditionalFieldsGroup).get(additional_fields_group_id)
    else:
        additional_fields_group = AdditionalFieldsGroup()

    form = Form(request, schema=AdditionalFieldsGroupSchema, obj=additional_fields_group)

    if form.validate():
        form.bind(additional_fields_group)

        db_session.add(additional_fields_group)

        return HTTPFound(request.route_url('list_additional_fields_groups'))

    return {'renderer': FormRenderer(form),
            'additional_fields_group': additional_fields_group if additional_fields_group.id else None}


@view_config(route_name='delete_additional_fields_group', permission='administration')
def delete_additional_fields_group(request):
    db_session = DBSession()
    additional_fields_group = db_session.query(AdditionalFieldsGroup).get(request.GET.get('id'))
    if additional_fields_group:
        spiders = db_session.query(Spider).filter(Spider.additional_fields_group_id == additional_fields_group.id).all()
        for s in spiders:
            s.additional_fields_group_id = None
            db_session.add(s)

        db_session.delete(additional_fields_group)

    return HTTPFound(request.route_url('list_additional_fields_groups'))


@view_config(route_name='set_starred_error', permission='administration')
def set_starred_error(request):
    if request.method == 'POST':
        spider_id = int(request.POST.get('id'))
        db_session = DBSession()
        spider_error = db_session.query(SpiderError).filter(SpiderError.spider_id == spider_id).first()
        spider_error.starred = True if not spider_error.starred else False
        db_session.add(spider_error)
        return Response(json={'starred': spider_error.starred})
    else:
        return HTTPBadRequest(json={'status': 'error'})

@view_config(route_name='check_crawl_method', permission='administration', renderer='json')
def check_crawl_method(request):
    spider_name = request.matchdict['spider']
    account_name = request.matchdict['account']
    crawl_method = request.params['method']

    # get spider class
    spcls = get_spider_class(account_name, spider_name)
    if not spcls:
        raise HTTPBadRequest(body="Could not find spider class for spider '%s' in account '%s'" %
                             (spider_name, account_name))
    # check
    if not crawl_method in CRAWL_METHOD_FIT_CHECK_FUNCS:
        raise HTTPBadRequest('Wrong crawl method')
    errors = CRAWL_METHOD_FIT_CHECK_FUNCS[crawl_method](spcls)

    if errors:
        return {'status': False, 'errors': errors}
    else:
        return {'status': True}

@view_config(route_name='spider_exceptions', renderer='spider_exceptions.mako', permission='administration')
def spider_exceptions(request):
    db_session = DBSession()
    res = db_session.query(SpiderException).order_by(desc(SpiderException.date)).all()

    for r in res:
        spider = db_session.query(Spider).get(r.spider_id)
        r.spider_name = spider.name

    return {'spider_exceptions': res}

@view_config(route_name='exception_log', permission='administration')
def exception_log(request):
    db_session = DBSession()
    ex = db_session.query(SpiderException).get(request.GET['id'])
    res = FileResponse(os.path.abspath(os.path.join(HERE, '../../data/exceptions/%s' % ex.log_name)))

    return res

@view_config(route_name='delisted_duplicates', renderer='delisted_duplicates.mako', permission='administration')
def delisted_duplicates(request):
    dashboard_menu = Menu()
    dashboard_menu.set_active('maintenance')
    return {'menu': dashboard_menu.get_iterable()}

@view_config(route_name='delisted_duplicates_data', renderer='json', permission='administration')
def delisted_duplicates_data(request):
    db_session = DBSession()

    limit = int(request.GET.get('limit', 50))
    offset = int(request.GET.get('offset', 0))
    search = request.GET.get('search')

    all_errors = db_session.query(DelistedDuplicateError).join(Crawl).join(Spider).join(SpiderError)\
       .filter(Crawl.status == 'errors_found',
               DelistedDuplicateError.fixed != True,
               Crawl.spider_id == SpiderError.spider_id,
               SpiderError.status != 'fixed')\
       .order_by(DelistedDuplicateError.website_id, Crawl.crawl_date)

    if search:
        all_errors = all_errors.filter(Spider.name.ilike('%' + search + '%'))

    errors = []
    count_q = all_errors.statement.with_only_columns([func.count()]).order_by(None)
    total = all_errors.session.execute(count_q).scalar()

    paged_errors = all_errors.offset(offset).limit(limit)

    if paged_errors.count() > 0:
        for e in paged_errors:
            errors.append({
                'id': e.id,
                'website_id': e.website_id,
                'website_name': e.spider.name,
                'crawl_date': e.crawl.crawl_date.strftime('%d/%m/%Y'),
                'fixed': e.fixed})

    return {'total': total, 'rows': errors}

@view_config(route_name='delisted_duplicates_export_errors_csv', permission='administration')
def delisted_duplicates_export_errors_csv(request):
    try:
        issue_id = int(request.GET.get('id', 0))
    except:
        issue_id = None
    if not issue_id:
        raise HTTPNotFound('Issue not found')
    db_session = DBSession()
    dd_error = db_session.query(DelistedDuplicateError).get(int(issue_id))
    if not dd_error:
        raise HTTPNotFound('Issue not found')

    filepath = os.path.join(DATA_DIR, dd_error.filename)
    if not os.path.exists(filepath):
        raise HTTPNotFound('Issue not found')
    r = FileResponse(filepath, request=request, content_type='text/csv')
    r.content_disposition = 'attachment; filename=%s_%s_errors.csv' % (dd_error.website_id, dd_error.crawl_id)

    return r

@view_config(route_name='delisted_duplicates_import_config', renderer='json', permission='administration')
def delisted_duplicates_import_config(request):
    db_session = DBSession()

    websites = [{'id': s.website_id,
                 'name': s.name}
        for s in db_session.query(Spider).join(SpiderError)\
            .filter(SpiderError.status != 'fixed',
                    SpiderError.error_type == 'identifier_change')]

    return {
        'websites': websites,
    }

@view_config(route_name='run_delisted_duplicates_import', renderer='json', permission='administration')
def run_delisted_duplicates_import(request):
    task_id = -1
    website_id = request.POST['website_id']
    input_file = request.POST['issues'].file
    filename = os.path.join('/tmp', '%s.csv' % uuid.uuid4())
    temp_filename = filename + '~'

    input_file.seek(0)
    with open(temp_filename, 'wb') as output_file:
        shutil.copyfileobj(input_file, output_file)

    os.rename(temp_filename, filename)

    task = import_delisted_duplicates_issues.apply_async(args=[website_id, filename], queue='fixes')
    task_id = task.id

    return {'task_id': task_id}

@view_config(route_name='delisted_duplicates_import_status', renderer='json', permission='administration')
def delisted_duplicates_import_status(request):
    task_id = request.GET.get('id')

    task = import_delisted_duplicates_issues.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 100),
            'status': task.info['status']
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        response = {
            'state': task.state,
            'current': 0,
            'total': 100,
            'status': str(task.info),
        }

    return response

@view_config(route_name='run_delisted_duplicates_fixer', renderer='json', permission='administration')
def run_delisted_duplicates_fixer(request):
    task_id = -1
    issue_id = request.GET.get('id', 0)
    task = fix_delisted_duplicates.apply_async(args=[issue_id], queue='fixes')
    task_id = task.id

    return {'task_id': task_id}

@view_config(route_name='delisted_duplicates_fixer_status', renderer='json', permission='administration')
def delisted_duplicates_fixer_status(request):
    task_id = request.GET.get('id')

    task = fix_delisted_duplicates.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 100),
            'status': task.info['status']
        }
    else:
        response = {
            'state': task.state,
            'current': 0,
            'total': 100,
            'status': str(task.info),
        }

    return response

@view_config(route_name='delisted_duplicates_detector_config', renderer='json', permission='administration')
def delisted_duplicates_detector_config(request):
    db_session = DBSession()

    websites = [{'id': s.website_id,
                 'name': s.name}
        for s in db_session.query(Spider).join(SpiderError)\
            .filter(SpiderError.status != 'fixed')]

    return {
        'websites': websites,
        'field_names': ['sku', 'name', 'url', 'image_url', 'price', 'dealer', 'identifier']
    }

@view_config(route_name='run_delisted_duplicates_detector', renderer='json', permission='administration')
def run_delisted_duplicates_detector(request):
    task_id = -1
    website_id = int(request.GET.get('website_id'))
    field_name = request.GET.getall('field_name')
    if not isinstance(field_name, list):
        field_name = [field_name]
    ignore_case = bool(request.GET.get('ignore_case', False))

    task = detect_duplicates.apply_async(args=[website_id, field_name, ignore_case], queue='fixes')
    task_id = task.id

    return {'task_id': task_id}

@view_config(route_name='delisted_duplicates_detector_status', renderer='json', permission='administration')
def delisted_duplicates_detector_status(request):
    task_id = request.GET.get('id')

    task = detect_duplicates.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 100),
            'status': task.info['status']
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        response = {
            'state': task.state,
            'current': 0,
            'total': 100,
            'status': str(task.info),
        }

    return response

@view_config(route_name='remove_duplicates', renderer='remove_duplicates.mako', permission='administration')
def remove_duplicates(request):
    db_session = DBSession()

    spiders = db_session.query(Spider).join(Account)\
        .filter(Spider.enabled == True,
                Account.enabled == True)

    dashboard_menu = Menu()
    dashboard_menu.set_active('maintenance')
    return {'menu': dashboard_menu.get_iterable(), 'spiders': spiders}

@view_config(route_name='run_remove_duplicates_task', renderer='json', permission='administration')
def run_remove_duplicates_task(request):
    task_id = -1
    spider_id = int(request.GET.get('spider_id', 0))
    detect = bool(request.GET.get('detect', False))

    if not detect:
        task = admin_remove_duplicates_task.apply_async(args=[spider_id])
    else:
        task = admin_detect_duplicates_task.apply_async(args=[spider_id])

    task_id = task.id

    return {'task_id': task_id}

@view_config(route_name='remove_duplicates_status', renderer='json', permission='administration')
def remove_duplicates_status(request):
    task_id = request.GET.get('id')
    detect = bool(request.GET.get('detect', False))

    if not detect:
        task = admin_remove_duplicates_task.AsyncResult(task_id)
    else:
        task = admin_detect_duplicates_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 100),
            'status': task.info['status']
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        response = {
            'state': task.state,
            'current': 0,
            'total': 100,
            'status': str(task.info),
        }

    return response

@view_config(route_name='admin_userlogs', renderer='admin_userlogs.mako', permission='administration')
def admin_userlogs(request):
    db_session = DBSession()

    spider_logs = [e[0] for e in db_session.query(UserLog.spider_id).distinct().all()]
    spiders = db_session.query(Spider.id, Spider.name)\
        .filter(Spider.id.in_(spider_logs))
    users = db_session.query(User)

    return {'spiders': spiders, 'users': users}

@view_config(route_name='spiders_user_log_report_data', renderer='json', permission='administration')
def spiders_user_log_data(request):
    db_session = DBSession()

    page = int(request.POST.get('page', 1) or 1)
    spiders_filter = request.POST.getall('spiders')
    users_filter = request.POST.getall('users')
    from_date = request.POST.get('from_date')
    to_date = request.POST.get('to_date')

    if type(spiders_filter) != list:
        spiders_filter = [spiders_filter]
    if type(users_filter) != list:
        users_filter = [users_filter]

    all_logs = db_session.query(UserLog, Spider)\
        .join(Spider, UserLog.spider_id == Spider.id)\
        .order_by(UserLog.date_time.desc())

    if spiders_filter:
        all_logs = all_logs.filter(UserLog.spider_id.in_(spiders_filter))
    if users_filter:
        all_logs = all_logs.filter(UserLog.username.in_(users_filter))
    if from_date:
        all_logs = all_logs.filter(UserLog.date_time >= from_date)
    if to_date:
        all_logs = all_logs.filter(UserLog.date_time <= to_date)

    user_logs = []
    count_q = all_logs.statement.with_only_columns([func.count()]).order_by(None)
    total_count = all_logs.session.execute(count_q).scalar()

    # Paging
    current_page = page
    if current_page > 0:
        page_size = 50
        all_pages = int(ceil(float(total_count) / float(page_size)))
        next_page = current_page + 1 if current_page < all_pages else 0
        prev_page = current_page - 1 if current_page > 1 else 0
        paged_logs = all_logs.offset((current_page - 1) * page_size).limit(page_size)

        paging_size = 15

        first_page = current_page - 5
        first_page = first_page if first_page > 0 else 1
        last_page = first_page + paging_size - 1
        last_page = last_page if last_page < all_pages else all_pages
    else:
        paged_logs = all_logs

    account_names = {}

    if paged_logs.count() > 0:
        for l in paged_logs:
            if l.Spider.account_id not in account_names:
                account_names[l.Spider.account_id] = db_session.query(Account).get(int(l.Spider.account_id)).name
            user_logs.append({
                'id': l.UserLog.id,
                'account_name': account_names[l.Spider.account_id],
                'website_name': l.Spider.name,
                'user_name': l.UserLog.name,
                'date_time': str(l.UserLog.date_time),
                'activity': l.UserLog.activity,
                'priority': 'Yes' if l.Spider.priority_possible_errors else ''})

    if current_page < 0:
        # Return all pages
        return user_logs

    return {'status': 200, 'data': {'user_logs': user_logs, 'pages': range(first_page, last_page + 1), 'total': total_count,
                                    'page': current_page, 'prev': prev_page, 'next': next_page}}

@view_config(route_name='renew_tor_ip', renderer='json', permission=Everyone)
def renew_tor_ip(request):
    proxy_str = request.POST.get('proxy')
    if not proxy_str:
        return {'status': 'error', 'msg': 'no proxy str'}

    from product_spiders.scripts.torinstances.torinstance_config import renew_ip_tor
    res = renew_ip_tor(proxy_str)
    if res:
        return {'status': 'ok'}
    else:
        return {'status': 'error', 'msg': 'proxy "%s" not found' % proxy_str}

# System to upload spiders
@view_config(route_name='spiders_upload', renderer='spiders_upload.mako', permission='spiders_upload')
def spiders_upload(request):
    db_session = DBSession()

    if request.method == 'POST':
        account_id = request.POST.get('account_id')
        user_id = request.POST.get('user_id')
        f = request.POST.get('spider_file').file
        notes = request.POST.get('notes').strip()
        data = f.read()
        spider_upload = SpiderUpload()
        if account_id != 'new_account':
            spider_upload.account_id = account_id
        spider_upload.user_id = user_id
        spider_upload.spider_file = data
        spider_upload.status = 'waiting'
        spider_upload.upload_time = datetime.now()
        spider_upload.notes = notes
        spider_name = ''
        for l in data.split('\n'):
            norm = l.replace(' ', '').replace('\t', '').replace("'", '').replace('"', '')
            if norm.startswith('name='):
                spider_name = norm.split('=')[1]
                break

        spider_upload.spider_name = spider_name
        db_session.add(spider_upload)

    dashboard_menu = Menu()
    dashboard_menu.set_active('maintenance')
    user = get_user(request)
    accounts = db_session.query(Account).order_by(Account.name).all()
    users = db_session.query(User).order_by(User.name).all()
    users = [u for u in users if u.is_deployer()]
    spider_uploads = db_session.query(SpiderUpload).order_by(desc(SpiderUpload.upload_time)).all()

    return {'menu': dashboard_menu.get_iterable(), 'spiders': spider_uploads, 'accounts': accounts,
            'users': users, 'user': user}


@view_config(route_name='download_spider_upload', permission='spiders_upload')
def download_spider_upload(request):
    db_session = DBSession()
    spider_upload_id = request.GET.get('id')
    spider_upload = db_session.query(SpiderUpload).get(spider_upload_id)
    f = NamedTemporaryFile(delete=False, suffix='.py', prefix='spider_')
    f.write(spider_upload.spider_file.encode('utf8'))
    f.close()
    r = FileResponse(f.name, request=request, content_type='text')
    r.content_disposition = 'attachment; filename=%s' % f.name.split('/')[-1]
    return r

@view_config(route_name='spider_upload_deployed', permission='spiders_upload')
def spider_upload_deployed(request):
    db_session = DBSession()
    spider_upload_id = request.GET.get('id')
    spider_upload = db_session.query(SpiderUpload).get(spider_upload_id)
    spider_upload.status = 'deployed'
    spider_upload.deployed_time = datetime.now()
    db_session.add(spider_upload)
    return HTTPFound(request.route_url('spiders_upload'))

@view_config(route_name='get_accounts_crawls_stats', renderer='json', permission=Everyone)
def get_accounts_crawls_stats(request):
    db_session = DBSession()

    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    if not from_date:
        return HTTPBadRequest
    else:
        from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
    if not to_date:
        to_date = date.today()
    else:
        to_date = datetime.strptime(to_date, '%Y-%m-%d').date()

    data = []

    accounts = db_session.query(Account)\
        .filter(Account.enabled == True)
    for account in accounts:
        account_data = {
            'account_name': account.name,
            'spiders_no': 0,
            'target_crawls_no': 0,
            'crawls_uploaded_no': 0,
        }
        spiders = db_session.query(Spider)\
            .filter(Spider.account_id == account.id,
                    Spider.enabled == True)
        account_data['spiders_no'] = spiders.count()
        for spider in spiders:
            first_crawl = db_session.query(Crawl.crawl_date)\
                .filter(Crawl.spider_id == spider.id,
                        Crawl.status == 'upload_finished')\
                .order_by(Crawl.crawl_date,
                          Crawl.id)\
                .limit(1)\
                .first()
            if not first_crawl:
                continue
            if first_crawl.crawl_date > from_date:
                first_date = first_crawl.crawl_date
            else:
                first_date = from_date
            total_days = (to_date - first_date).days + 1
            run_times = 1  # Default (daily spider)
            cron_enabled = False
            if spider.enable_multicrawling and (spider.crawls_per_day or spider.account.crawls_per_day):
                # Multicrawling method used
                run_times = spider.crawls_per_day or spider.account.crawls_per_day
            elif spider.crawl_cron:
                # This spider use cron
                cron_enabled = True
                run_times = 0
                from_date_tmp = first_date
                while from_date_tmp <= to_date:
                    if is_cron_today(*spider.crawl_cron.split()[2:], dt=from_date_tmp):
                        run_times += 1
                    from_date_tmp += timedelta(days=1)

            if cron_enabled:
                target_crawls_no = run_times
            else:
                target_crawls_no = total_days * run_times
            crawls_uploaded_no = db_session.query(func.count(Crawl.id))\
                .filter(Crawl.spider_id == spider.id,
                        Crawl.status == 'upload_finished',
                        Crawl.crawl_date >= first_date,
                        Crawl.crawl_date <= to_date)\
                .scalar()
            account_data['target_crawls_no'] += target_crawls_no
            account_data['crawls_uploaded_no'] += crawls_uploaded_no

        data.append(account_data)

    return data


@view_config(route_name='get_spiders_crawls_stats', renderer='json', permission=Everyone)
def get_spiders_crawls_stats(request):
    db_session = DBSession()

    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    cm_account_id = request.GET.get('cm_account_id', '')
    if not from_date:
        return HTTPBadRequest
    else:
        from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
    if not to_date:
        to_date = date.today()
    else:
        to_date = datetime.strptime(to_date, '%Y-%m-%d').date()

    data = []

    accounts = db_session.query(Account.id, Account.name)\
        .filter(Account.enabled == True)
    if cm_account_id:
        accounts = accounts.filter(Account.member_id == int(cm_account_id))
    accounts_dict = {}
    for account in accounts:
        accounts_dict[account.id] = account.name
    spiders = db_session.query(Spider)\
        .filter(Spider.enabled == True,
                Spider.account_id.in_(accounts_dict.keys()))
    for spider in spiders:
        spider_data = {
            'spider_name': spider.name,
            'account_name': accounts_dict[spider.account_id],
            'target_crawls_no': 0,
            'crawls_uploaded_no': 0,
        }
        first_crawl = db_session.query(Crawl.crawl_date)\
            .filter(Crawl.spider_id == spider.id,
                    Crawl.status == 'upload_finished')\
            .order_by(Crawl.crawl_date,
                      Crawl.id)\
            .limit(1)\
            .first()
        if not first_crawl:
            continue
        if first_crawl.crawl_date > from_date:
            first_date = first_crawl.crawl_date
        else:
            first_date = from_date
        total_days = (to_date - first_date).days + 1
        run_times = 1  # Default (daily spider)
        cron_enabled = False
        if spider.enable_multicrawling and (spider.crawls_per_day or spider.account.crawls_per_day):
            # Multicrawling method used
            run_times = spider.crawls_per_day or spider.account.crawls_per_day
        elif spider.crawl_cron:
            # This spider use cron
            cron_enabled = True
            run_times = 0
            from_date_tmp = first_date
            while from_date_tmp <= to_date:
                if is_cron_today(*spider.crawl_cron.split()[2:], dt=from_date_tmp):
                    run_times += 1
                from_date_tmp += timedelta(days=1)

        if cron_enabled:
            target_crawls_no = run_times
        else:
            target_crawls_no = total_days * run_times
        crawls_uploaded_no = db_session.query(func.count(Crawl.id))\
            .filter(Crawl.spider_id == spider.id,
                    Crawl.status == 'upload_finished',
                    Crawl.crawl_date >= from_date,
                    Crawl.crawl_date <= to_date)\
            .scalar()
        spider_data['target_crawls_no'] += target_crawls_no
        spider_data['crawls_uploaded_no'] += crawls_uploaded_no

        data.append(spider_data)

    return data


@view_config(route_name='get_spiders_upload_stats', renderer='json', permission=Everyone)
def get_spiders_upload_stats(request):
    db_session = DBSession()

    date_filter = request.GET.get('date_filter', '')
    cm_account_id = request.GET.get('cm_account_id', '')
    if not date_filter:
        return HTTPBadRequest

    date_filter = datetime.strptime(date_filter, '%Y-%m-%d').date()

    data = []

    accounts = db_session.query(Account.id, Account.name)\
        .filter(Account.enabled == True)
    if cm_account_id:
        accounts = accounts.filter(Account.member_id == int(cm_account_id))
    accounts_dict = {}
    for account in accounts:
        accounts_dict[account.id] = account.name
    spiders = db_session.query(Spider)\
        .filter(Spider.enabled == True,
                Spider.account_id.in_(accounts_dict.keys()))
    for spider in spiders:
        last_crawl = db_session.query(Crawl)\
            .filter(Crawl.spider_id == spider.id,
                    Crawl.crawl_date == date_filter)\
            .order_by(Crawl.id.desc())\
            .first()

        spider_data = {
            'spider_priority': spider.priority_possible_errors,
            'spider_name': spider.name,
            'account_name': accounts_dict[spider.account_id],
            'setup_start_hour': spider.start_hour,
            'setup_start_minute': spider.start_minute,
            'start_time': str(last_crawl.start_time or '') if last_crawl else '',
            'end_time': str(last_crawl.end_time or '') if last_crawl else '',
            'setup_upload_hour': spider.upload_hour,
            'uploaded_time': str(last_crawl.uploaded_time or '') if last_crawl else '',
        }

        data.append(spider_data)

    return data


@view_config(route_name='get_latest_scrapy_stats', renderer='scrapy_latest_stats.mako', permission=Everyone)
def get_latest_scrapy_stats(request):
    db_session = DBSession()
    spiders_success = db_session.query(Spider, Account).join(Account)\
                                .join(Crawl).filter(Crawl.worker_server_id == 10000005,
                                                    Crawl.status == 'upload_finished').all()

    spiders_pending = db_session.query(Spider, Account).join(Account)\
                                .join(Crawl).filter(Crawl.worker_server_id == 10000005).all()
    spiders_success_ids = set([s.Spider.id for s in spiders_success])
    spiders_pending = [s for s in spiders_pending if s.Spider.id not in spiders_success_ids]

    return {'spiders_success': spiders_success, 'spiders_pending': spiders_pending}


@view_config(route_name='get_crawlers_weekly_report', renderer='json', permission=Everyone)
def get_crawlers_weekly_report(request):
    db_session = DBSession()
    # Total # of real and possible errors in the past 7 days
    today = date.today()
    to_ = today
    from_ = today - timedelta(days=6)
    daily_errors = db_session.query(DailyErrors).filter(DailyErrors.date.between(from_, to_)).order_by(DailyErrors.date)
    total_real_errors = 0
    total_possible_errors = 0
    for daily_stat in daily_errors:
        total_real_errors += int(daily_stat.real if daily_stat.real else 0)
        total_possible_errors += int(daily_stat.possible if daily_stat.possible else 0)
    # Average number of possible errors we had over the past 7 days
    possible_errors_avg = int(round(float(total_possible_errors) / float(7)))
    # Current number of real errors in the system
    current_real_errors_count = db_session.query(Spider)\
        .join(SpiderError).filter(SpiderError.status == 'real').count()
    # Top 5 sites With Errors
    spider_errors = db_session.query(SpiderError)\
        .filter(SpiderError.time_added < today,
                SpiderError.time_added >= (today - timedelta(days=30)))\
        .order_by(SpiderError.time_added)
    spiders_total_errors = {}
    error_types_total = {}
    for spider_error in spider_errors:
        if spider_error.spider_id not in spiders_total_errors:
            spiders_total_errors[spider_error.spider_id] = 1
        else:
            spiders_total_errors[spider_error.spider_id] += 1
        if spider_error.error_type != 'awaiting_feedback':
            if spider_error.error_type not in error_types_total:
                error_types_total[spider_error.error_type] = 1
            else:
                error_types_total[spider_error.error_type] += 1
    top_five_spiders = sorted(spiders_total_errors.items(), key=lambda item: item[1], reverse=True)[:5]
    top_five_types = sorted(error_types_total.items(), key=lambda item: item[1], reverse=True)[:5]

    conn = db_session.connection()

    current_day = from_
    total_last_updated_sites = 0
    while current_day <= today:
        last_updated_sites = conn.execute(text('select count(s.id) from spider s join account a on(s.account_id = a.id) '
            'where s.enabled and (s.crawl_cron is null or s.crawl_cron = \'* * * * *\') and a.enabled and s.id in (select c.spider_id from crawl c join spider s2 on '
            '(c.spider_id = s2.id) join account a2 on (s2.account_id = a2.id) where s2.enabled and a2.enabled '
            'and c.status = \'upload_finished\' and c.end_time < :current_day group by c.spider_id having '
            'date_part(\'day\', :current_day - max(c.end_time)) >= 2);'), current_day=current_day).fetchone()
        total_last_updated_sites += int(last_updated_sites['count'])
        current_day += timedelta(days=1)
    last_updated_sites_avg = int(round(float(total_last_updated_sites) / float(7)))

    top_five_spiders_details = []
    for i, (sid, total) in enumerate(top_five_spiders):
        spider_name = db_session.query(Spider).get(sid).name
        top_five_spiders_details.append((i + 1, spider_name, total))

    top_five_types_details = []
    for i, (tid, total) in enumerate(top_five_types):
        type_name = ERROR_TYPES_DICT[tid]
        top_five_types_details.append((i + 1, type_name, total))

    return {
        'total_real_errors': total_real_errors,
        'current_real_errors_count': current_real_errors_count,
        'possible_errors_avg': possible_errors_avg,
        'top_five_spiders': top_five_spiders_details,
        'top_five_types': top_five_types_details,
        'last_updated_sites_avg': last_updated_sites_avg,
    }


@view_config(route_name='edit_rating', renderer='spider_edit_rating.mako', permission='administration', request_method='GET')
def edit_rating_view(request):
    if not request.session.peek_flash('edit_rating_referrer'):
        if request.referrer != request.url:
            request.session.flash(request.referrer, queue='edit_rating_referrer')
    account_name = request.matchdict['account']
    spider_name = request.matchdict['spider']
    db_session = DBSession()
    account = db_session.query(Account).filter(Account.name == account_name).first()
    spider = db_session.query(Spider).filter(Spider.name == spider_name).filter(Spider.account_id == account.id).first()
    params = get_spider_rating_params(db_session, spider)

    status = None
    msg = None
    flash = request.session.pop_flash()
    if flash and len(flash) == 2:
        status, msg = flash
    elif flash:
        msg = flash[0]

    return {
        'edit_spider_rating': request.route_url('edit_rating', account=account_name, spider=spider_name),
        'spider': spider,
        'metrics_schema': get_metrics_schema(),
        'message': msg,
        'status': status,
        'params': params
    }

@view_config(route_name='edit_rating', permission='administration', request_method='POST')
def edit_rating(request):
    referrer = request.session.pop_flash(queue='edit_rating_referrer')
    if referrer:
        referrer = referrer[0]
    else:
        referrer = request.url
    account_name = request.matchdict['account']
    spider_name = request.matchdict['spider']
    db_session = DBSession()
    account = db_session.query(Account).filter(Account.name == account_name).first()
    spider = db_session.query(Spider).filter(Spider.name == spider_name).filter(Spider.account_id == account.id).first()

    params = process_ratings_form(request.params)
    save_spider_rating(db_session, spider, params)

    request.session.flash("OK")
    request.session.flash("Spider rating updated")
    return HTTPFound(referrer)


@view_config(route_name='last_log_file', permission=Everyone, request_method='GET')
def last_log_file(request):
    db_session = DBSession()
    spider = request.GET.get('spider')
    if spider:
        spider = db_session.query(Spider).filter(Spider.name == spider).first()
    if not spider:
        return HTTPNotFound()

    crawl_id = request.GET.get('crawl_id')

    if not crawl_id:
        last_crawl = db_session.query(Crawl)\
                    .filter(Crawl.spider_id == spider.id)\
                    .order_by(Crawl.crawl_date.desc(),
                              desc(Crawl.id)).limit(1).first()
    else:
        last_crawl = db_session.query(Crawl)\
                    .filter(Crawl.spider_id == spider.id, Crawl.id == crawl_id).first()

    if not last_crawl:
        return HTTPNotFound()

    url = get_log_crawl(db_session, spider, last_crawl)

    return HTTPFound(location=url)


epoch = datetime.utcfromtimestamp(0)

def unix_time(dt):
    return int((dt - epoch).total_seconds() * 1000.0)


@view_config(route_name='get_running_crawl_stats', permission='maintenance',
             renderer='running_crawl_stats.mako', request_method='GET')
def get_running_crawl_stats(request):
    db_session = DBSession()
    crawl_id = request.GET.get('crawl_id')

    crawl = db_session.query(Crawl).get(crawl_id)
    if not crawl:
        return HTTPNotFound()
    spider = db_session.query(Spider).get(crawl.spider_id)
    filename = os.path.join(DATA_DIR, '{}_crawl_stats.csv'.format(crawl.id))
    stats = []
    if os.path.exists(filename):
        with open(filename) as f:
            reader = csv.reader(f)
            for row in reader:
                stats.append(row)

    items, pages, irate, prate = 0, 0, 0.0, 0.0
    if stats:
        last_stats = stats[-1]
        items, pages = int(last_stats[0]), int(last_stats[1])
        irate, prate = float(last_stats[2]), float(last_stats[3])

    products_per_minute = []
    pages_per_minute = []
    t = crawl.start_time
    for s in stats:
        products_per_minute.append([unix_time(t), int(float(s[2]))])
        pages_per_minute.append([unix_time(t), int(float(s[3]))])
        t = t + timedelta(minutes=1)

    previous_crawl = db_session.query(Crawl).filter(Crawl.spider_id == spider.id,
                                                    Crawl.id < crawl.id)\
                                .order_by(desc(Crawl.crawl_date), desc(Crawl.id)).first()
    total_previous = 0
    perc = None
    if previous_crawl:
        total_previous = previous_crawl.products_count
        if total_previous:
            perc = float(items * 100) / total_previous

    if crawl.status in ['upload_finished', 'processing_finished', 'errors_found']:
        items = crawl.products_count
        perc = 100

    return {'crawl': crawl, 'spider': spider, 'items': items, 'pages': pages,
            'irate': int(irate), 'prate': int(prate), 'products_per_minute': json.dumps(products_per_minute),
            'pages_per_minute': json.dumps(pages_per_minute), 'perc': int(perc) if perc is not None else perc}
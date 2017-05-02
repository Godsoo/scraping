import transaction
import sys
import os.path
import datetime
import json

from sqlalchemy import Column
from sqlalchemy import Integer, BigInteger
from sqlalchemy import String, Unicode, UnicodeText
from sqlalchemy import Date
from sqlalchemy import ForeignKey
from sqlalchemy import Enum
from sqlalchemy import Boolean
from sqlalchemy import Time, DateTime
from sqlalchemy import Table
from sqlalchemy import desc
from sqlalchemy import Float

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship

from zope.sqlalchemy import ZopeTransactionExtension

from productspidersweb.utils import CRAWL_STATUSES, SPIDER_ERROR_STATUSES

HERE = os.path.dirname(__file__)
path = os.path.abspath(os.path.join(HERE, '../..'))

DATA_DIR = os.path.join(path, 'data')

sys.path.append(path)
path = os.path.join(path, 'product_spiders')

sys.path.append(path)

from product_spiders.config import upload_destinations

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
DBSessionSimple = sessionmaker()
Base = declarative_base()

ERROR_TYPES = [
    ('identifier', 'Identifier'),
    ('identifier_change', 'Identifier change'),
    ('duplicates', 'Non-unique Identifier'),
    ('missing_identifier', 'Missing Identifier'),
    ('crawler_bug', 'Crawler Bug'),
    ('xpath', 'XPath not valid'),
    ('ajax', 'AJAX error'),
    ('data_integrity', 'Data Integrity error'),
    ('programming_error', 'Programming error'),
    ('performance', 'Performance issues'),
    ('wrong_setup', 'Incorrect configuration'),
    ('proxies', 'Tor and proxies'),
    ('site_down', 'Site change/down'),
    ('blocked', 'Blocked'),
    ('maintenance', 'Maintenance'),
    ('awaiting_feedback', 'Awaiting Feedback'),
    ('other', 'Other'),
]


class Account(Base):
    """ Model class for accounts. """
    __tablename__ = 'account'
    id = Column(Integer, primary_key=True)
    name = Column(String(256), unique=True)
    member_id = Column(Integer, unique=True)
    enabled = Column(Boolean, nullable=False, index=True)
    upload_keter_system = Column(Boolean, nullable=False, default=False)
    upload_new_system = Column(Boolean, nullable=False, default=False)
    upload_new_and_old = Column(Boolean, nullable=False, default=False)
    crawls_per_day = Column(Integer)
    map_screenshots = Column(Boolean, default=False)
    spiders = relationship('Spider', backref='account')
    notification_receivers = relationship('NotificationReceiver', backref='account')

class Crawl(Base):
    """ Model class for crawls. """
    __tablename__ = 'crawl'
    id = Column(Integer, primary_key=True)
    crawl_date = Column(Date, nullable=False, index=True)
    crawl_time = Column(Time)
    spider_id = Column(ForeignKey('spider.id'), nullable=False, index=True)
    status = Column(Enum(*CRAWL_STATUSES, name='status'), nullable=False, index=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)

    uploaded_time = Column(DateTime)

    products_count = Column(Integer, nullable=False, default=0)

    changes_count = Column(Integer, nullable=False, default=0)
    additions_count = Column(Integer, nullable=False, default=0)
    deletions_count = Column(Integer, nullable=False, default=0)
    updates_count = Column(Integer, nullable=False, default=0)
    additional_changes_count = Column(Integer, nullable=False, default=0)

    worker_server_id = Column(ForeignKey('worker_server.id'))

    error_message = Column(UnicodeText)

    jobid = Column(Unicode(32))

    stats = relationship('CrawlStats', backref='spider', uselist=False, cascade="all,delete")

    retry = Column(Boolean, default=False)

    scheduled_time = Column(DateTime)
    scheduled_on_worker_time = Column(DateTime)

    def __init__(self, crawl_date, spider, status='running'):
        self.crawl_date = crawl_date
        self.spider = spider
        self.status = status

class CrawlHistory(Base):
    __tablename__ = 'crawl_history'
    id = Column(Integer, primary_key=True)
    crawl_id = Column(ForeignKey('crawl.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False)

    final_status = Column(Enum(*CRAWL_STATUSES, name='status'), nullable=False, index=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)

    products_count = Column(Integer, nullable=False, default=0)

    changes_count = Column(Integer, nullable=False, default=0)
    additions_count = Column(Integer, nullable=False, default=0)
    deletions_count = Column(Integer, nullable=False, default=0)
    updates_count = Column(Integer, nullable=False, default=0)
    additional_changes_count = Column(Integer, nullable=False, default=0)

    discarted = Column(Boolean, default=False)
    discarted_reason = Column(UnicodeText)

    def __init__(self, crawl_obj):
        self.crawl_id = crawl_obj.id
        self.final_status = crawl_obj.status
        self.start_time = crawl_obj.start_time
        self.end_time = crawl_obj.end_time

        self.products_count = crawl_obj.products_count

        self.changes_count = crawl_obj.changes_count
        self.additions_count = crawl_obj.additions_count
        self.deletions_count = crawl_obj.deletions_count
        self.updates_count = crawl_obj.updates_count
        self.additional_changes_count = crawl_obj.additional_changes_count


class Spider(Base):
    """ Model class for spiders. """
    __tablename__ = 'spider'
    id = Column(Integer, primary_key=True)
    name = Column(String(256), unique=True, index=True)
    website_id = Column(Integer, unique=True)
    start_hour = Column(Integer)
    start_minute = Column(Integer, default=0)
    upload_hour = Column(Integer)
    timezone = Column(String(1024))
    crawl_day = Column(Integer)
    enabled = Column(Boolean, default=True, nullable=False)
    automatic_upload = Column(Boolean, default=True, nullable=False)

    update_percentage_error = Column(String(10))
    additions_percentage_error = Column(String(10))
    deletions_percentage_error = Column(String(10))
    price_updates_percentage_error = Column(String(10))
    additional_changes_percentage_error = Column(String(10))
    stock_percentage_error = Column(String(10))

    max_price_change_percentage = Column(String(10))

    add_changes_empty_perc = Column(String(10))
    image_url_perc = Column(String(10))
    category_change_perc = Column(String(10))
    sku_change_perc = Column(String(10))

    use_proxies = Column(Boolean, default=False, nullable=False)
    use_tor = Column(Boolean, default=False, nullable=False)
    use_cache = Column(Boolean, default=False, nullable=False)
    # expiration time in seconds, default 24 hours
    cache_expiration = Column(Integer, default=86400, nullable=False)
    # cache storage type: redis+postgres or SSDB
    cache_storage = Column(Enum('REDIS_POSTGRES', 'SSDB', name='http_cache_storage'), nullable=True, default=None)
    upload_testing_account = Column(Boolean, default=False, nullable=False)
    price_conversion_rate = Column(String(10))
    enable_metadata = Column(Boolean, default=False, nullable=False)
    silent_updates = Column(Boolean, default=False, nullable=False)
    enable_multicrawling = Column(Boolean, default=False, nullable=False)
    priority = Column(Integer)
    priority_possible_errors = Column(Boolean, default=False)
    account_id = Column(ForeignKey('account.id'), nullable=False, index=True)
    crawls = relationship('Crawl', backref='spider', order_by='Crawl.crawl_date, Crawl.id')
    notification_receivers = relationship('NotificationReceiver', backref='spider')

    concurrent_requests = Column(Integer, default=8)
    disable_cookies = Column(Boolean, default=False)

    rerun = Column(Boolean, default=False)
    error = relationship(lambda: SpiderError, uselist=False, backref='spider', order_by=lambda: desc(SpiderError.time_added))
    notes = relationship('Note', backref='spider')
    hide_disabled = Column(Boolean, default=False)
    check_deletions = Column(Boolean, default=False)
    proxy_list_id = Column(ForeignKey('proxy_list.id'))
    worker_server_id = Column(ForeignKey('worker_server.id'))
    additional_fields_group_id = Column(ForeignKey('worker_server.id'))

    parse_method = Column(String(10), default='unknown')

    immutable_metadata = Column(UnicodeText)

    # big site method of other crawl method
    crawl_method2 = relationship('CrawlMethod', backref='spider', uselist=False)

    # scrapely spider configuration if spider is from Visual Tool
    scrapely_data = relationship('ScrapelySpiderData', backref='spider', uselist=False)

    # Users logs
    users_logs = relationship('UserLog', backref='spider')

    # Not uploaded alert receivers
    not_uploaded_alert_receivers = Column(UnicodeText)

    # Proxy Service
    proxy_service_enabled = Column(Boolean, default=False)
    proxy_service_target = Column(Integer)
    proxy_service_profile = Column(Integer)
    proxy_service_types = Column(UnicodeText)
    proxy_service_locations = Column(UnicodeText)
    proxy_service_length = Column(Integer)
    proxy_service_algorithm = Column(Integer)

    tor_renew_on_retry = Column(Boolean, default=False)

    reviews_mandatory = Column(Boolean, default=False)

    crawls_per_day = Column(Integer)

    ignore_identifier_changes = Column(Boolean)
    ignore_additional_changes = Column(UnicodeText)
    ignore_connection_errors = Column(Boolean)

    automatic_retry_enabled = Column(Boolean, default=True)
    automatic_retries_max = Column(Integer, default=3)

    crawl_cron = Column(String(32))

    module = Column(UnicodeText)

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'website_id': self.website_id,
            'start_hour': self.start_hour,
            'start_minute': self.start_minute,
            'upload_hour': self.upload_hour,
            'crawl_day': self.crawl_day,
            'enabled': self.enabled,
            'automatic_upload': self.automatic_upload,
            'update_percentage_error': self.update_percentage_error,
            'additions_percentage_error': self.additions_percentage_error,
            'deletions_percentage_error': self.deletions_percentage_error,
            'price_updates_percentage_error': self.price_updates_percentage_error,
            'additional_changes_percentage_error': self.additional_changes_percentage_error,
            'stock_percentage_error': self.stock_percentage_error,
            'max_price_change_percentage': self.max_price_change_percentage,
            'add_changes_empty_perc': self.add_changes_empty_perc,
            'image_url_perc': self.image_url_perc,
            'category_change_perc': self.category_change_perc,
            'sku_change_perc': self.sku_change_perc,
            'use_proxies': self.use_proxies,
            'use_tor': self.use_tor,
            'use_cache': self.use_cache,
            'cache_expiration': self.cache_expiration,
            'cache': self.cache_storage,
            'upload_testing_account': self.upload_testing_account,
            'price_conversion_rate': self.price_conversion_rate,
            'enable_metadata': self.enable_metadata,
            'silent_updates': self.silent_updates,
            'enable_multicrawling': self.enable_multicrawling,
            'priority': self.priority,
            'priority_possible_errors': self.priority_possible_errors,
            'account_id': self.account_id,
            'notification_receivers': self.notification_receivers,
            'concurrent_requests': self.concurrent_requests,
            'disable_cookies': self.disable_cookies,
            'rerun': self.rerun,
            'hide_disabled': self.hide_disabled,
            'check_deletions': self.check_deletions,
            'proxy_list_id': self.proxy_list_id,
            'worker_server_id': self.worker_server_id,
            'additional_fields_group_id': self.additional_fields_group_id,
            'parse_method': self.parse_method,
            'immutable_metadata': self.immutable_metadata,
            'not_uploaded_alert_receivers': self.not_uploaded_alert_receivers,
            'proxy_service_enabled': self.proxy_service_enabled,
            'proxy_service_target': self.proxy_service_target,
            'proxy_service_profile': self.proxy_service_profile,
            'proxy_service_types': self.proxy_service_types,
            'proxy_service_locations': self.proxy_service_locations,
            'proxy_service_length': self.proxy_service_length,
            'proxy_service_algorithm': self.proxy_service_algorithm,
            'tor_renew_on_retry': self.tor_renew_on_retry,
            'reviews_mandatory': self.reviews_mandatory,
            'crawls_per_day': self.crawls_per_day,
            'ignore_identifier_changes': self.ignore_identifier_changes,
            'ignore_additional_changes': self.ignore_additional_changes,
            'ignore_connection_errors': self.ignore_connection_errors,
            'automatic_retry_enabled': self.automatic_retry_enabled,
            'automatic_retries_max': self.automatic_retries_max,
            'crawl_cron': self.crawl_cron,
        }


class SpiderDefault(Base):
    __tablename__ = 'spider_default'
    id = Column(Integer, primary_key=True)
    automatic_upload = Column(Boolean, default=True, nullable=False)
    silent_updates = Column(Boolean, default=False, nullable=False)
    update_percentage_error = Column(String(10))
    additions_percentage_error = Column(String(10))
    deletions_percentage_error = Column(String(10))
    price_updates_percentage_error = Column(String(10))
    additional_changes_percentage_error = Column(String(10))
    stock_percentage_error = Column(String(10))
    max_price_change_percentage = Column(String(10))
    add_changes_empty_perc = Column(String(10))
    image_url_perc = Column(String(10))
    category_change_perc = Column(String(10))
    sku_change_perc = Column(String(10))

class ProxyList(Base):
    __tablename__ = 'proxy_list'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    proxies = Column(UnicodeText, nullable=False)

class NotificationReceiver(Base):
    __tablename__ = 'notification_receiver'
    id = Column(Integer, primary_key=True)
    email = Column(String(256), nullable=False)
    account_id = Column(ForeignKey('account.id'), nullable=False)
    spider_id = Column(ForeignKey('spider.id'))
    status = Column(Enum(*CRAWL_STATUSES, name='status'))

    def __init__(self, email, status, account, spider):
        self.email = email
        self.status = status
        self.account = account
        self.spider = spider

class SpiderError(Base):
    __tablename__ = "spider_error"
    id = Column(Integer, primary_key=True)
    spider_id = Column(ForeignKey('spider.id'), nullable=False, index=True)
    time_added = Column(DateTime)
    time_fixed = Column(DateTime)
    status = Column(Enum(*SPIDER_ERROR_STATUSES, name="error_status"), nullable=False, index=True)
    assigned_to = Column(String(256))
    assigned_to_id = Column(ForeignKey('developer.id'))
    assembla_ticket_id = Column(String(256))
    starred = Column(Boolean, default=False)
    error_type = Column(String(20))
    error_desc = Column(String(1024))

class Note(Base):
    __tablename__ = "note"
    id = Column(Integer, primary_key=True)
    spider_id = Column(ForeignKey('spider.id'), nullable=False, index=True)
    time_added = Column(DateTime)
    text = Column(String(1024))

class DailyErrors(Base):
    __tablename__ = "daily_errors"
    id = Column(Integer, primary_key=True)
    possible = Column(Integer, default=0)
    real = Column(Integer, default=0)
    date = Column(Date)

account_upload_destination_table = Table(
    'account_upload_destination', Base.metadata,
    Column('account_id', Integer, ForeignKey('account.id')),
    Column('upload_destination_id', Integer, ForeignKey('upload_destination.id'))
)

class UploadDestination(Base):
    """
    Model for upload destination types (keter, old system, new system, etc)
    """
    __tablename__ = "upload_destination"

    id = Column(Integer, primary_key=True)
    name = Column(String(256), unique=True)
    type = Column(Enum('old', 'new', name='destination_type'), nullable=False, default=True)

    accounts = relationship("Account", secondary=account_upload_destination_table, backref="upload_destinations")

class WorkerServer(Base):
    __tablename__ = "worker_server"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    host = Column(String(100), nullable=False)
    user = Column(String(100), nullable=False)
    password = Column(String(100), nullable=False)
    port = Column(Integer, nullable=False)
    scrapy_url = Column(String(100), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    worker_slots = Column(Integer, default=5)

class DeletionsReview(Base):
    """
    Model for reviewing product deletions
    """
    __tablename__ = "deletions_review"
    id = Column(Integer, primary_key=True)
    crawl_date = Column(Date)
    found_date = Column(Date)
    account_name = Column(String(256))
    site = Column(String(256))
    product_name = Column(String(256))
    matched = Column(Boolean, nullable=False, default=False)
    url = Column(String(1024))
    dealer = Column(String(256))
    status = Column(String(256))
    spider_id = Column(ForeignKey('spider.id'))
    crawl_id = Column(ForeignKey('crawl.id'))
    assigned_to = Column(String(256))
    assembla_ticket_id = Column(String(256))

class AdditionalFieldsGroup(Base):
    __tablename__ = 'additional_fields_group'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, default=True)
    enable_url = Column(Boolean, nullable=False, default=True)
    enable_name = Column(Boolean, nullable=False, default=True)
    enable_category = Column(Boolean, nullable=False, default=True)
    enable_brand = Column(Boolean, nullable=False, default=True)
    enable_image_url = Column(Boolean, nullable=False, default=True)
    enable_weekly_updates = Column(Boolean, nullable=False, default=False)

class CrawlMethod(Base):
    __tablename__ = 'crawl_method'
    id = Column(Integer, primary_key=True)
    spider_id = Column(ForeignKey('spider.id'), nullable=False, index=True)
    crawl_method = Column(String(255), default=None)
    _params = Column(UnicodeText, default=None)

    @property
    def params(self):
        return json.loads(self._params)

    @params.setter
    def params(self, value):
        if value is not None:
            self._params = json.dumps(value)
        else:
            self._params = None

class ScrapelySpiderData(Base):
    __tablename__ = 'scrapely_spider_data'
    id = Column(Integer, primary_key=True)
    spider_id = Column(ForeignKey('spider.id'), nullable=False, index=True)
    start_url = Column(String(255), nullable=False)
    start_urls_json = Column(UnicodeText, nullable=False)

    extractors = relationship('ScrapelySpiderExtractor', backref='scrapely_spider_data')

class ScrapelySpiderExtractor(Base):
    __tablename__ = 'scrapely_spider_extractor'
    id = Column(Integer, primary_key=True)
    scrapely_spider_data_id = Column(ForeignKey('scrapely_spider_data.id'), nullable=False, index=True)
    type = Column(Enum('links_list', 'product_details', name="page_type"), nullable=False)
    templates_json = Column(UnicodeText, nullable=False)
    fields_spec_json = Column(UnicodeText, nullable=False)

class CrawlStats(Base):
    __tablename__ = 'crawl_stats'
    crawl_id = Column(ForeignKey('crawl.id', onupdate='CASCADE', ondelete='CASCADE'), primary_key=True)

    request_count = Column(BigInteger, nullable=False, index=True)
    request_bytes = Column(BigInteger, nullable=False, index=True)
    response_count = Column(BigInteger, nullable=False, index=True)
    response_bytes = Column(BigInteger, nullable=False, index=True)

    item_scraped_count = Column(BigInteger, nullable=False, index=True)
    item_dropped_count = Column(BigInteger, nullable=False, index=True)

    stats_json = Column(UnicodeText, nullable=False)

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    username = Column(String(256), unique=True, index=True)
    password = Column(String(512))
    name = Column(String(256), unique=True, index=True)
    login_disabled = Column(Boolean) # This user can not log in
    email = Column(String(256))

    def set_password(self, pswd):
        def sha256(string):
            import hashlib
            m = hashlib.sha256()
            m.update(string)
            return m.hexdigest()

        self.password = sha256(pswd)

    def is_admin(self):
        return ('administration' in self.groups)

    # spider uploader to upload system
    def is_uploader(self):
        return ('uploader' in self.groups)

    def is_deployer(self):
        return ('deployer' in self.groups)

    @property
    def groups(self):
        db_session = DBSession()
        return [g.name for g in db_session.query(UserGroup)\
                    .filter(UserGroup.username == self.username)]

class Group(Base):
    __tablename__ = "group"
    id = Column(Integer, primary_key=True)
    name = Column(String(256), unique=True, index=True)

class UserGroup(Base):
    __tablename__ = "user_group"
    id = Column(Integer, primary_key=True)
    name = Column(ForeignKey('group.name', onupdate='CASCADE', ondelete='CASCADE'))
    username = Column(ForeignKey('user.username', onupdate='CASCADE', ondelete='CASCADE'))

class UserLog(Base):
    __tablename__ = "user_log"
    id = Column(Integer, primary_key=True)
    username = Column(ForeignKey('user.username', onupdate='CASCADE', ondelete='CASCADE'))
    name = Column(ForeignKey('user.name', onupdate='CASCADE', ondelete='CASCADE'))
    spider_id = Column(ForeignKey('spider.id', onupdate='CASCADE', ondelete='CASCADE'))
    activity = Column(String(256))
    date_time = Column(DateTime)

class Developer(Base):
    __tablename__ = "developer"
    id = Column(Integer, primary_key=True)
    name = Column(String(256), unique=True)
    assembla_id = Column(String(256))
    active = Column(Boolean, default=True)

    @property
    def total_assigned(self):
        db_session = DBSession()
        return db_session.query(SpiderError)\
                .filter(SpiderError.status == 'real',
                        SpiderError.assigned_to_id == self.id).count()

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'assembla_id': self.assembla_id,
            'active': self.active,
        }

class SpiderResourcesUsage(Base):
    __tablename__ = "spider_resources_usage"
    id = Column(Integer, primary_key=True)
    spider_id = Column(ForeignKey('spider.id', onupdate='CASCADE', ondelete='CASCADE'))
    worker_server_id = Column(ForeignKey('worker_server.id'))
    cpu_usage = Column(Float)
    mem_usage = Column(Float)
    time = Column(DateTime)

class SpiderException(Base):
    __tablename__ = 'spider_exception'
    id = Column(Integer, primary_key=True)
    spider_id = Column(ForeignKey('spider.id', onupdate='CASCADE', ondelete='CASCADE'), index=True)
    date = Column(Date, index=True)
    log_name = Column(String(100))
    exceptions = Column(UnicodeText)
    total = Column(Integer)

class SpiderErrorType(Base):
    __tablename__ = 'spider_error_type'
    id = Column(Integer, primary_key=True)
    code = Column(Integer, nullable=False, unique=True, index=True)
    description = Column(String(512), nullable=False)
    severity_level = Column(Integer, nullable=False, default=3)
    group_id = Column(ForeignKey('spider_error_group.id'))

class SpiderErrorGroup(Base):
    __tablename__ = 'spider_error_group'
    id = Column(Integer, primary_key=True)
    name = Column(String(512), nullable=False)
    error_types = relationship('SpiderErrorType', backref='group',
                               order_by=lambda: SpiderErrorType.severity_level.asc())

class DelistedDuplicateError(Base):
    __tablename__ = 'delisted_duplicate_error'
    id = Column(Integer, primary_key=True)
    website_id = Column(ForeignKey('spider.website_id', onupdate='CASCADE', ondelete='CASCADE'), index=True)
    spider = relationship('Spider', backref='delistes_duplicate_errors')
    crawl_id = Column(ForeignKey('crawl.id', onupdate='CASCADE', ondelete='CASCADE'))
    crawl = relationship('Crawl', backref='delisted_duplicate_errors')
    filename = Column(String(1024))
    fixed = Column(Boolean, default=False)

class SpiderUpload(Base):
    __tablename__ = 'spider_upload'
    id = Column(Integer, primary_key=True)
    spider_file = Column(UnicodeText)
    account_id = Column(ForeignKey('account.id'))
    upload_time = Column(DateTime, nullable=False)
    deployed_time = Column(DateTime)
    user_id = Column(ForeignKey('user.id'), nullable=False)
    notes = Column(UnicodeText)
    status = Column(Enum('waiting', 'deployed', name='spider_upload_status'), nullable=False)
    last_notification = Column(DateTime)
    spider_name = Column(UnicodeText)
    account = relationship('Account')
    user = relationship('User')


class SpiderDoc(Base):
    """ Table to store cache of spider documentation """
    __tablename__ = 'spider_doc'
    spider_id = Column(ForeignKey('spider.id'), primary_key=True)
    latest_changeset = Column(String(255), index=True)
    branch = Column(String(255), index=True)
    _data = Column(UnicodeText, nullable=False)

    @property
    def data(self):
        return json.loads(self._data)

    @data.setter
    def data(self, value):
        if value is not None:
            self._data = json.dumps(value)
        else:
            self._data = None


class SpiderRating(Base):
    __tablename__ = 'spider_rating'
    spider_id = Column(ForeignKey('spider.id'), primary_key=True)
    score = Column(Integer, default=0, index=True)
    _params = Column(UnicodeText, default=None)

    @property
    def params(self):
        return json.loads(self._params)

    @params.setter
    def params(self, value):
        if value is not None:
            self._params = json.dumps(value)
        else:
            self._params = None


class SpiderSpec(Base):
    """ Table to store spider spec """
    __tablename__ = 'spider_spec'
    spider_id = Column(ForeignKey('spider.id'), primary_key=True)
    _data = Column(UnicodeText, nullable=False)

    @property
    def data(self):
        return json.loads(self._data)

    @data.setter
    def data(self, value):
        if value is not None:
            self._data = json.dumps(value)
        else:
            self._data = None


def add_default_upload_destinations(db_session):
    for destination_name, settings in upload_destinations.items():
        dst = db_session.query(UploadDestination).filter(UploadDestination.name == destination_name).first()
        if not dst:
            upload_destination = UploadDestination()
            upload_destination.name = destination_name
            upload_destination.type = settings['type']
            with transaction.manager:
                db_session.add(upload_destination)

def add_default_worker_server(db_session):
    worker_server = db_session.query(WorkerServer).filter(WorkerServer.name == 'Default').first()
    if not worker_server:
        worker_server = WorkerServer()
        worker_server.name = 'Default'
        worker_server.host = '127.0.0.1'
        worker_server.user = 'innodev'
        worker_server.password = 'innodev'
        worker_server.port = 22
        worker_server.scrapy_url = 'http://localhost:6800/'
        with transaction.manager:
            db_session.add(worker_server)

def initialize_sql(engine, create_ws=True):
    # Index("ix_spider_error_spider_id_status", SpiderError.spider_id, SpiderError.status)
    # Index("ix_spider_name_account_id", Spider.name, Spider.account_id)

    DBSession.configure(bind=engine)
    DBSessionSimple.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)

    add_default_upload_destinations(DBSession())
    if create_ws:
        add_default_worker_server(DBSession())

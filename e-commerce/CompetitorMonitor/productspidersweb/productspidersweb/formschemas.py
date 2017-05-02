import re

import formencode
from formencode import Schema, validators, FancyValidator
from formencode.declarative import DeclarativeMeta

from models import (
    DBSession,
    UploadDestination
)

from utils import UI_CRAWL_STATUSES

EMAIL_RE = "^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$"
URL_RE = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

class EmailList(FancyValidator):
    def _to_python(self, value, state):
        if not value.strip():
            return []

        email_list = [email.strip() for email in value.split(',')]
        for email in email_list:
            if not re.match(EMAIL_RE, email):
                raise formencode.Invalid('Invalid format for email addresses', value, state)

        return email_list

class EmailSchema(DeclarativeMeta):
    def __new__(cls, name, bases, dct):
        for status in UI_CRAWL_STATUSES:
            dct[status + '_emails'] = EmailList()

        return super(EmailSchema, cls).__new__(cls, name, bases, dct)

class ProxyList(FancyValidator):
    def _to_python(self, value, state):
        if not value.strip():
            raise formencode.Invalid('Proxies field is empty', value, state)

        proxies_list = [proxy.strip() for proxy in value.split('\n')]

        return '\n'.join(proxies_list)

class ProxyServiceList(FancyValidator):
    accept_iterator = True
    if_missing = ''

    def _to_python(self, value, state):
        if isinstance(value, (str, unicode)):
            return value
        else:
            return '|'.join(value)

class AdditionalFieldChangesList(FancyValidator):
    accept_iterator = True
    if_missing = ''

    def _to_python(self, value, state):
        if isinstance(value, (str, unicode)):
            return value
        else:
            return '|'.join(value)

class ImmutableMetaList(FancyValidator):
    def _to_python(self, value, state):
        if not value.strip():
            return ''

        return value

class EmailListPlainText(FancyValidator):
    def _to_python(self, value, state):
        if not value.strip():
            return ''

        email_list = [email.strip() for email in value.split(',')]
        for email in email_list:
            if not re.match(EMAIL_RE, email):
                raise formencode.Invalid('Invalid format for email addresses', value, state)

        return value

class AccountSchema(Schema):
    __metaclass__ = EmailSchema

    filter_extra_fields = True
    allow_extra_fields = True

    member_id = validators.Int(not_empty=True, min=1)
    enabled = validators.Bool(not_empty=True)
    upload_keter_system = validators.Bool(not_empty=True)
    upload_new_system = validators.Bool(not_empty=True)
    upload_new_and_old = validators.Bool(not_empty=True)
    crawls_per_day = validators.Int(min=1)
    map_screenshots = validators.Bool(not_empty=True)

    def __init__(self, *args, **kwargs):
        for upload_dst in DBSession().query(UploadDestination).all():
            self.add_field('upload_to_' + upload_dst.name, validators.Bool(not_empty=True))

class SpiderSchema(Schema):
    __metaclass__ = EmailSchema

    filter_extra_fields = True
    allow_extra_fields = True

    website_id = validators.Int(not_empty=True, min=1)
    start_hour = validators.Int(not_empty=True, min=0, max=23)
    start_minute = validators.Int(not_empty=True, min=0, max=59)
    upload_hour = validators.Int(not_empty=True, min=0, max=23)
    enabled = validators.Bool(not_empty=True)
    automatic_upload = validators.Bool(not_empty=True)
    use_proxies = validators.Bool(not_empty=True)
    use_tor = validators.Bool(not_empty=True)
    upload_testing_account = validators.Bool(not_empty=True)

    use_cache = validators.Bool(not_empty=True)
    cache_expiration = validators.Int()
    cache_storage = validators.String()

    update_percentage_error = validators.Number(min=0)
    additions_percentage_error = validators.Number(min=0)
    deletions_percentage_error = validators.Number(min=0)
    price_updates_percentage_error = validators.Number(min=0)
    additional_changes_percentage_error = validators.Number(min=0)
    stock_percentage_error = validators.Number(min=0)
    add_changes_empty_perc = validators.Number(min=0)
    image_url_perc = validators.Number(min=0)
    category_change_perc = validators.Number(min=0)
    sku_change_perc = validators.Number(min=0)
    max_price_change_percentage = validators.Number(min=0)
    price_conversion_rate = validators.Number(min=0)
    enable_metadata = validators.Bool(not_empty=True)
    silent_updates = validators.Bool(not_empty=True)
    enable_multicrawling = validators.Bool(not_empty=True)
    priority = validators.Int()

    priority_possible_errors = validators.Bool(not_empty=True)
    check_deletions = validators.Bool(not_empty=True)

    concurrent_requests = validators.Number(min=1)
    disable_cookies = validators.Bool(not_empty=True)
    proxy_list_id = validators.Int(min=1)

    worker_server_id = validators.Int(min=1)
    additional_fields_group_id = validators.Int(min=1)

    immutable_metadata = ImmutableMetaList()

    not_uploaded_alert_receivers = EmailListPlainText()

    proxy_service_enabled = validators.Bool(not_empty=True)
    proxy_service_target = validators.Int(min=1)
    proxy_service_profile = validators.Int(min=1)
    proxy_service_types = ProxyServiceList()
    proxy_service_locations = ProxyServiceList()
    proxy_service_length = validators.Int(min=1)
    proxy_service_algorithm = validators.Int(min=0)

    tor_renew_on_retry = validators.Bool(not_empty=True)

    reviews_mandatory = validators.Bool(not_empty=True)

    crawls_per_day = validators.Int(min=0)
    ignore_identifier_changes = validators.Bool(not_empty=True)
    ignore_additional_changes = AdditionalFieldChangesList()
    ignore_connection_errors = validators.Bool(not_empty=True)

    automatic_retry_enabled = validators.Bool(not_empty=True)
    automatic_retries_max = validators.Int(min=0)

    crawl_cron = validators.String()
    timezone = validators.String()

class ProxyListSchema(Schema):
    filter_extra_fields = True
    allow_extra_fields = True

    name = validators.PlainText(not_empty=True)
    proxies = ProxyList()

class WorkerServerSchema(Schema):
    filter_extra_fields = True
    allow_extra_fields = True

    name = validators.NotEmpty()
    host = validators.NotEmpty()
    user = validators.NotEmpty()
    password = validators.NotEmpty()
    port = validators.Int(not_empty=True)
    scrapy_url = validators.NotEmpty()
    enabled = validators.Bool()

class AdditionalFieldsGroupSchema(Schema):
    filter_extra_fields = True
    allow_extra_fields = True
    name = validators.NotEmpty()
    enable_url = validators.Bool()
    enable_name = validators.Bool()
    enable_category = validators.Bool()
    enable_brand = validators.Bool()
    enable_image_url = validators.Bool()
    enable_weekly_updates = validators.Bool()

class AssemblaTicketSchema(Schema):
    id = validators.Int(not_empty=True)
    summary = validators.UnicodeString()
    description = validators.UnicodeString()
    assign_to = validators.String()
    upload_source_file = validators.Bool(not_empty=True)

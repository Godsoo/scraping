# -*- coding: utf-8 -*-

import csv
import time
from celery import task

from productspidersweb.models import (
    DailyErrors,
    Account,
    Spider,
    SpiderError,
    Crawl,
    ERROR_TYPES,
    Developer,
)
from db import Session
from sqlalchemy import desc
from sqlalchemy.sql import func

import config
from emailnotifier import EmailNotifier
from contrib.compmon2 import Compmon2API


@task
def send_enabled_accounts_report(receivers):
    db_session = Session()


    header = ['Account', 'Number of spiders', 'Number of primary spiders', 'Number of spiders using BSM',
              'Number of products in account (In Stock and Out of Stock)', 'Number of matches (client SKUs)',
              'Match rate', 'Main Offender', 'Common Error Type']

    accounts = db_session.query(Account)\
        .filter(Account.enabled == True)

    api_host = ''
    api_key = '3Df7mNg'

    f = open('/tmp/enabled_accounts_report_%s.csv' % str(time.time()).split('.')[0], 'w')
    writer = csv.writer(f)
    writer.writerow(header)

    error_types = dict(ERROR_TYPES)

    for account in accounts:

        upload_dst = account.upload_destinations[0].name if account.upload_destinations else ''
        if upload_dst in config.new_system_api_roots:
            api_host = config.new_system_api_roots[upload_dst]
        else:
            continue

        compmon_api = Compmon2API(api_host, api_key)
        try:
            main_website_id = compmon_api.get_main_website_id(account.member_id)
            total_products = compmon_api.get_products_total_account(account.member_id)
            matched_products = compmon_api.get_matches_count_website(main_website_id)
            match_rate = compmon_api.get_match_rate_website(main_website_id)
        except:
            continue

        new_row = [account.name]
        spiders = db_session.query(Spider)\
            .filter(Spider.account_id == account.id,
                    Spider.enabled == True)
        account_spider_ids = [s.id for s in spiders]

        main_offender = ''
        main_error = db_session.query(SpiderError.spider_id, func.count(SpiderError.id).label('errors'))\
            .filter(SpiderError.spider_id.in_(account_spider_ids))\
            .group_by(SpiderError.spider_id).order_by(desc('errors')).first()
        if main_error:
            main_offender = '%s (%s)' % (db_session.query(Spider).get(main_error.spider_id).name, main_error.errors)

        common_error_type = ''
        main_error = db_session.query(SpiderError.error_type, func.count(SpiderError.id).label('errors'))\
            .filter(SpiderError.spider_id.in_(account_spider_ids))\
            .group_by(SpiderError.error_type).order_by(desc('errors')).first()
        if main_error:
            common_error_type = error_types[main_error.error_type]

        new_row.append(str(spiders.count()))
        new_row.append(str(spiders.filter(Spider.parse_method != 'Secondary').count()))
        new_row.append(str(spiders.filter(Spider.parse_method == 'BSM').count()))
        new_row.append(str(total_products))
        new_row.append(str(matched_products))
        new_row.append(str(match_rate))
        new_row.append(main_offender)
        new_row.append(common_error_type)

        writer.writerow(new_row)

    f.close()

    db_session.close()

    notifier = EmailNotifier(config.SMTP_USER, config.SMTP_PASS,
                             config.SMTP_FROM, config.SMTP_HOST,
                             config.SMTP_PORT)
    notifier.send_notification(receivers, 'Enabled Accounts Report', 'Please find attached the report', attachments=[f.name])

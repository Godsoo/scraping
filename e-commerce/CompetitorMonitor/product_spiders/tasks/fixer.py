# -*- coding: utf-8 -*-

from celery import task
from fixers import DelistedDuplicateFixer

"""

Delisted Duplicates Errors

"""

@task(bind=True)
def fix_delisted_duplicates(self, issue_id):

    current_status = {
        'current': 0,
        'total': 100,
        'status': 'Processing changes'}

    dd_fixer = DelistedDuplicateFixer(issue_id, self.request.id)

    self.update_state(state='WORKING',
                      meta=current_status)

    current_status['status'] = 'Fixing CSV'
    self.update_state(state='WORKING',
                      meta=current_status)
    dd_fixer.fix_csv()

    current_status['current'] = 90
    current_status['status'] = 'Closing'
    self.update_state(state='WORKING',
                      meta=current_status)
    dd_fixer.close()
    current_status['current'] = 100
    current_status['status'] = 'Completed'

    return current_status

@task(bind=True)
def detect_duplicates(self, website_id, field_name, ignore_case):
    current_status = {
        'current': 10,
        'total': 100,
        'status': 'Processing...'}

    self.update_state(state='WORKING',
                      meta=current_status)

    total = DelistedDuplicateFixer.detect_issues(website_id, field_name, True, ignore_case)

    current_status['current'] = 100
    current_status['status'] = 'Completed'
    current_status['result'] = total

    return current_status

@task(bind=True)
def import_delisted_duplicates_issues(self, website_id, filename):
    current_status = {
        'current': 10,
        'total': 100,
        'status': 'Processing...'}

    self.update_state(state='WORKING',
                      meta=current_status)

    DelistedDuplicateFixer.import_issues(website_id, filename)

    current_status['current'] = 100
    current_status['status'] = 'Completed'
    current_status['result'] = ''

    return current_status

"""

Admin Tasks

"""

import json
from fixers import AdminTasks

@task(bind=True)
def admin_detect_duplicates_task(self, spider_id):

    current_status = {
        'current': 10,
        'total': 100,
        'status': 'Processing...'}

    self.update_state(state='WORKING',
                      meta=current_status)

    duplicates = AdminTasks.detect_duplicates(spider_id)

    current_status['current'] = 100
    current_status['status'] = 'Completed'
    current_status['result'] = json.dumps(duplicates)

    return current_status

@task(bind=True)
def admin_remove_duplicates_task(self, spider_id):

    current_status = {
        'current': 10,
        'total': 100,
        'status': 'Processing...'}

    self.update_state(state='WORKING',
                      meta=current_status)

    total = AdminTasks.remove_duplicates(spider_id)

    current_status['current'] = 100
    current_status['status'] = 'Completed'
    current_status['result'] = total

    return current_status

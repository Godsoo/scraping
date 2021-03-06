import sys

sys.path.append('../..')

from config import BROKER_URL
from celery import Celery

celery = Celery(broker=BROKER_URL)
celery.send_task('product_spiders.tasks.reports.send_enabled_accounts_report', [['emr.frei@gmail.com']], queue='reports')

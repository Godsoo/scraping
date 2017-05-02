import sys

sys.path.append('../..')

from config import BROKER_URL
from celery import Celery

TO = ['toni.fleck@intelligenteye.com', 'steven.seaward@intelligenteye.com']


celery = Celery(broker=BROKER_URL)
celery.send_task('product_spiders.tasks.default.sites_not_uploaded_account_2', [TO, 120, 'Micheldever: sites not uploaded'])

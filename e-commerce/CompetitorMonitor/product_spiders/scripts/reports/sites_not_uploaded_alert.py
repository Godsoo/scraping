import sys

sys.path.append('../..')

from config import BROKER_URL
from celery import Celery

celery = Celery(broker=BROKER_URL)
celery.send_task('product_spiders.tasks.default.sites_not_uploaded', [])

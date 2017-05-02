import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE,
                                             '../../productspidersweb')))

from productspidersweb.models import Spider, Crawl
sys.path.append('..')

from db import Session
from scheduler import upload_required
from uploader import Uploader, UploaderException, upload_changes
from emailnotifier import EmailNotifier, EmailNotifierException
import config
from utils import get_receivers
from datetime import datetime


def _send_notification(notifier, crawl, spider):
        receivers = get_receivers(crawl.spider, crawl.status)
        if receivers:
            subject = config.EMAIL_MESSAGES[crawl.status]['subject'] % {'spider': spider.name}
            body = config.EMAIL_MESSAGES[crawl.status]['body'] % {'spider': spider.name}
            notifier.send_notification(receivers, subject, body)

def upload_crawls(db_session):
    notifier = EmailNotifier(config.SMTP_USER, config.SMTP_PASS,
                             config.SMTP_FROM, config.SMTP_HOST,
                             config.SMTP_PORT)

    uploader = Uploader()
    crawls = db_session.query(Spider).join(Crawl).\
             filter(Spider.enabled == True, 
                    Crawl.status.in_(['processing_finished', 'upload_errors']))
    for spider in crawls.all():
        if upload_required(spider):
            if spider.crawls[-1].products_count < 1:
                print 'Not uploading crawl with 0 products'
                continue
            print 'Uploading for', spider.name
            try:
                upload_changes(uploader, spider)
                spider.crawls[-1].status = 'upload_finished'
                spider.crawls[-1].uploaded_time = datetime.now()
            except Exception:
                spider.crawls[-1].status = 'upload_errors'

            db_session.add(spider.crawls[-1])
            db_session.commit()

            try:
                _send_notification(notifier, spider.crawls[-1], spider)
            except EmailNotifierException, e:
                print "Failed to send notifications: %s" % e

if __name__ == '__main__':
    db_session = Session()
    upload_crawls(db_session)

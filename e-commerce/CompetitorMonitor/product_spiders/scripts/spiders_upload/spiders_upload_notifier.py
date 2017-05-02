import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from product_spiders.emailnotifier import EmailNotifier
from product_spiders.config import *
from product_spiders.db import Session
from productspidersweb.models import SpiderUpload


class SpiderUploadNotificationScheduler(object):
    def should_send_initial(self, spider_upload):
        return spider_upload.status == 'waiting' and spider_upload.last_notification is None

    def should_send_reminder(self, spider_upload):
        return spider_upload.status == 'waiting' and spider_upload.last_notification and \
               spider_upload.last_notification + timedelta(hours=1) < datetime.now()

    def should_send_final(self, spider_upload):
        return spider_upload.status == 'deployed' and (not spider_upload.last_notification or
                                                       spider_upload.last_notification <= spider_upload.deployed_time)


TO = ['steven.seaward@intelligenteye.com', 'stephen.sharp@intelligenteye.com']

def main():
    db_session = Session()
    scheduler = SpiderUploadNotificationScheduler()
    e = EmailNotifier(SMTP_USER, SMTP_PASS, SMTP_FROM, SMTP_HOST, SMTP_PORT)
    spider_uploads = db_session.query(SpiderUpload).all()
    for s in spider_uploads:
        if not s.user.email:
            continue
        if scheduler.should_send_initial(s):
            subject = 'Spider upload request %s' % s.spider_name
            text = 'A spider upload has been assigned to you:\n'
            text += 'Account: %s\n' % (s.account.name if s.account else 'New account')
            text += 'Spider: %s\n' % s.spider_name
            if s.notes:
                text += 'Notes: %s' % s.notes
            e.send_notification([s.user.email] + TO, subject, text)
            print s.user.email
            s.last_notification = datetime.now()
            db_session.add(s)
        elif scheduler.should_send_final(s):
            subject = 'Spider deployed %s' % s.spider_name
            text = 'The following spider has been deployed:\n'
            text += 'Account: %s\n' % (s.account.name if s.account else 'New account')
            text += 'Spider: %s\n' % s.spider_name
            if s.notes:
                text += 'Notes: %s' % s.notes
            e.send_notification([s.user.email] + TO, subject, text)
            s.last_notification = datetime.now()
            db_session.add(s)
        elif scheduler.should_send_reminder(s):
            subject = 'Spider upload reminder %s' % s.spider_name
            text = 'The following spider has been assigned to you:\n'
            text += 'Account: %s\n' % (s.account.name if s.account else 'New account')
            text += 'Spider: %s\n' % s.spider_name
            if s.notes:
                text += 'Notes: %s' % s.notes
            e.send_notification([s.user.email], subject, text)
            s.last_notification = datetime.now()
            db_session.add(s)

        db_session.commit()


if __name__ == '__main__':
    main()
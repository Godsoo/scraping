# -*- coding: utf-8 -*-
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE,
                                             '../../productspidersweb')))

from productspidersweb.models import Spider, Account, account_upload_destination_table, UploadDestination
sys.path.append('..')

from db import Session

from uploadfulllistingwebsite import upload_fulllisting

if __name__ == "__main__":
    db_session = Session()

    accounts = db_session.query(Account).filter(Account.enabled == True)\
        .join(account_upload_destination_table)\
        .join(UploadDestination).filter(UploadDestination.name == 'new_system')

    count = 0
    for account in accounts:
        spiders = db_session.query(Spider).filter(Spider.account_id == account.id)\
            .filter(Spider.enabled == True)

        for spider in spiders:
            try:
                upload_fulllisting(db_session, spider.website_id)
            finally:
                count += 1

    print "Uploaded %d crawl results" % count
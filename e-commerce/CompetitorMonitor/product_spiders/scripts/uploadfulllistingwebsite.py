# -*- coding: utf-8 -*-
import sys
import os

from sqlalchemy import desc, and_
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE,
                                             '../../productspidersweb')))

from productspidersweb.models import Spider, Crawl, Account
sys.path.append('..')

from db import Session
from uploader import Uploader, UploaderException, upload_changes
from export import export_changes_new
from productsupdater import ProductsUpdater
import config

DATA_DIR = os.path.abspath(os.path.join(HERE, '../../data'))

def upload_fulllisting(db_session, website_id, ignore_disabled=True):
    spiders = db_session.query(Spider).filter(Spider.website_id == website_id)
    if ignore_disabled:
        spiders = spiders.filter(Spider.enabled == True)
    for spider in spiders:
        account = db_session.query(Account).get(spider.account_id)
        crawl = db_session.query(Crawl)\
                          .filter(and_(Crawl.spider_id == spider.id, Crawl.status == 'upload_finished'))\
                          .order_by(desc(Crawl.crawl_date)).first()

        if not crawl:
            continue

        uploader = Uploader()
        path = os.path.join(DATA_DIR, '%s_products.csv' % crawl.id)

        if not os.path.exists(path):
            print "Crawl results not found for %s. Skipping..." % (spider.name)
            continue

        for upload_dst in account.upload_destinations:
            while True:
                upload_config = config.upload_destinations[upload_dst.name]
                server_data = config.SERVERS[upload_config['server']]
                if 'folder_full_listing' not in upload_config:
                    break

                uploader.set_host_data(server_data['host'], server_data['user'], server_data['password'], server_data['port'])

                try:
                    print 'Uploading %s %s' % (spider.name, crawl.crawl_date.strftime('%Y-%m-%d'))
                    filename = '%s.csv' % (spider.website_id, )
                    uploader.upload_file(path, os.path.join(upload_config['folder_full_listing'], filename))
                    break
                except Exception, e:
                    raise e

        if spider.enable_metadata:
            path_meta = os.path.join(DATA_DIR, 'meta/%s_meta.json' % crawl.id)
            file_format = 'json'
            if not os.path.exists(path_meta):
                file_format = 'json-lines'
                path_meta = os.path.join(DATA_DIR, 'meta/%s_meta.json-lines' % crawl.id)
            if not os.path.exists(path_meta):
                raise Exception("Can find metadata file. Files do not exists: \n%s\n%s" % (
                    os.path.join(DATA_DIR, 'meta/%s_meta.json' % crawl.id),
                    os.path.join(DATA_DIR, 'meta/%s_meta.json-lines' % crawl.id)
                ))
            for upload_dst in account.upload_destinations:
                while True:
                    upload_config = config.upload_destinations[upload_dst.name]
                    server_data = config.SERVERS[upload_config['server']]
                    if 'folder_full_listing_meta' not in upload_config:
                        break

                    uploader.set_host_data(server_data['host'], server_data['user'],
                                           server_data['password'], server_data['port'])

                    try:
                        print 'Uploading metadata %s %s' % (spider.name, crawl.crawl_date.strftime('%Y-%m-%d'))
                        filename = '%s.%s' % (spider.website_id, file_format)
                        uploader.upload_file(path_meta, os.path.join(upload_config['folder_full_listing_meta'], filename))
                        break
                    except Exception, e:
                        raise e

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print "Usage %s <website id>"
        sys.exit(1)

    db_session = Session()
    website_id = sys.argv[1]

    only_enabled = True
    if len(sys.argv) > 2:
        if sys.argv[2] == 'all':
            only_enabled = False

    upload_fulllisting(db_session, website_id, only_enabled)



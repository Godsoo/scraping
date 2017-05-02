import os
import tempfile

import paramiko

import config
from export import export_changes
from productsupdater import ProductsUpdater

class UploaderException(Exception):
    pass

class Uploader(object):
    def __init__(self, host=config.SFTP_HOST, user=config.SFTP_USER,
                 passwd=config.SFTP_PASSWD, port=config.SFTP_PORT):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.port = port

    def set_host_data(self, host, user, passwd, port):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.port = port

    def upload_file(self, localpath, remotepath):
        try:
            transport = paramiko.Transport((self.host, self.port))
            transport.connect(username=self.user, password=self.passwd)

            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.put(localpath, remotepath)

            sftp.close()
            transport.close()
        except paramiko.SSHException, e:
            raise UploaderException(e.message)

def upload_changes(uploader, spider):
    crawl = spider.crawls[-1]

    upload_crawl_changes(uploader, crawl)

def upload_crawl_changes(uploader, crawl):
    member_id = crawl.spider.account.member_id
    if crawl.spider.upload_testing_account:
        member_id = config.TESTING_ACCOUNT

    for upload_dst in crawl.spider.account.upload_destinations:
        upload_config = config.upload_destinations[upload_dst.name]
        server_data = config.SERVERS[upload_config['server']]
        uploader.set_host_data(server_data['host'], server_data['user'], server_data['password'], server_data['port'])

        if upload_dst.type == 'old':
            path = os.path.join(config.DATA_DIR, '%s_changes_old.csv' % crawl.id)
            filename = '%s-%s.csv' % (member_id, crawl.spider.website_id)
        else:
            path = os.path.join(config.DATA_DIR, '%s_changes_new.csv' % crawl.id)
            if crawl.crawl_time:
                filename = '%s-%s-%s-%s.csv' % (member_id, crawl.spider.website_id, str(crawl.crawl_date),
                                                crawl.crawl_time.strftime('%H-%M'))
            else:
                filename = '%s-%s-%s.csv' % (member_id, crawl.spider.website_id, str(crawl.crawl_date))

        if not os.path.exists(path):
            path = os.path.join(config.DATA_DIR, '%s_changes.csv' % crawl.id)

        dst_changes = upload_config['folder']
        dst_meta = upload_config['folder_meta']

        uploader.upload_file(path, os.path.join(dst_changes, filename))

        if crawl.spider.enable_metadata:
            filename = '%s-%s-%s.json' % (member_id, crawl.spider.website_id, str(crawl.crawl_date))
            path = os.path.join(config.DATA_DIR, 'meta/%s_meta_changes.json' % crawl.id)
            if not os.path.exists(path):
                filename = '%s-%s-%s.json-lines' % (member_id, crawl.spider.website_id, str(crawl.crawl_date))
                path = os.path.join(config.DATA_DIR, 'meta/%s_meta_changes.json-lines' % crawl.id)
            if os.path.exists(path):
                uploader.upload_file(path, os.path.join(dst_meta, filename))

        additional_path = os.path.join(config.DATA_DIR, 'additional/%s_changes.json' % crawl.id)
        file_type = "json"
        if not os.path.exists(additional_path):
            additional_path = os.path.join(config.DATA_DIR, 'additional/%s_changes.json-lines' % crawl.id)
            file_type = "json-lines"
        if upload_config.get('folder_additional') and os.path.exists(additional_path) and crawl.additional_changes_count:
            if crawl.crawl_time:
                add_filename = '%s-%s-%s-%s.%s' % (member_id, crawl.spider.website_id, str(crawl.crawl_date),
                                                crawl.crawl_time.strftime('%H-%M'), file_type)
            else:
                add_filename = '%s-%s-%s.%s' % (member_id, crawl.spider.website_id, str(crawl.crawl_date), file_type)

            uploader.upload_file(additional_path, os.path.join(upload_config['folder_additional'], add_filename))





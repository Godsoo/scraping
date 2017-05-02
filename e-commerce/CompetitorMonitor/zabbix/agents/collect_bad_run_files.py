#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
The script collects files with "bad run" spiders lists from all slaves.
Then check for each spider in "bad run" lists if it's still running, and if so - output as error
"""
import sys
import shutil
import paramiko

import psycopg2
import psycopg2.extras

# change to proper host
DB_CONN_STR = "host=localhost dbname=productspiders user=productspiders"

local_ip = '148.251.79.44'


def download_spider_names_file(server):
    filename = 'bad_run_{server_id}.txt'.format(server_id=server['id'])
    remote_filepath = '/home/{user}/{filename}'.format(filename=filename, **server)
    if server['host'] == local_ip:
        # just copy file
        shutil.copy(remote_filepath, filename)
    else:
        transport = paramiko.Transport((server['host'], server['port']))
        transport.connect(username=server['user'], password=server['password'])
        sftp = paramiko.SFTPClient.from_transport(transport)

        remote_filepath = '/home/{user}/{filename}'.format(filename=filename, **server)
        sftp.get(remote_filepath, filename)

    return filename


def check_spider_names(cur, filename):
    with open(filename) as f:
        spider_names = [x.strip() for x in f]

    errors = []
    for spider_name in spider_names:
        cur.execute("select * from crawl where status in ('scheduled', 'running') AND spider_id in "
                    "(select s.id from spider s join account a on a.id = s.account_id "
                    "where s.enabled and a.enabled and s.name=%s)", (spider_name, ))
        if cur.fetchone():
            errors.append(spider_name)
    return errors


def main():
    conn = psycopg2.connect(DB_CONN_STR)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("select * from worker_server where id in "
                "(select worker_server_id from crawl where status in ('scheduled', 'running'))")

    errors = []
    files_collected = []
    for server in cur:
        # download file from server using SCP
        filename = download_spider_names_file(server)
        files_collected.append(filename)

        errors += check_spider_names(cur, filename)
    return errors


if __name__ == '__main__':
    errors = main()

    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        for spider_name in errors:
            print spider_name
    else:
        if len(errors):
            print 'f'
        else:
            print 't'

#!/usr/bin/python

import os
import shutil
import sqlite3
import psycopg2
import sys
from datetime import date, datetime
import subprocess

DB = 'postgres'

if DB == 'sqlite':
    here = os.path.dirname(os.path.abspath(__file__))

    db_dir = '/home/innodev/product-spiders/productspidersweb/'
    db_filename = 'productspidersweb.db'

    shutil.copy(os.path.join(db_dir, db_filename), here)

    conn = sqlite3.connect(os.path.join(here, db_filename))

else:
    conn = psycopg2.connect("dbname=productspiders user=productspiders")

c = conn.cursor()
c.execute('''SELECT COUNT(*) FROM crawl WHERE
             status='running' ''')

running = c.fetchone()[0]
MAX_RUNNING = 60

if DB == 'sqlite':
    c.execute('''SELECT spider.id, spider.name, account.name FROM spider INNER JOIN account ON spider.account_id=account.id
                 WHERE spider.enabled=1 and account.enabled=1''')
else:
    c.execute('''SELECT spider.id, spider.name, account.name FROM spider INNER JOIN account ON spider.account_id=account.id
                 WHERE spider.enabled=true and account.enabled=true and spider.worker_server_id is null or spider.worker_server_id = 1''')

invalid_spiders = []

for spider_id, spider_name, account_name in c.fetchall():
    if DB == 'sqlite':
        c.execute('''select crawl_date, status from crawl where spider_id=?
                     order by crawl_date desc, crawl_time desc limit 1;''', (spider_id,))
    else:
        c.execute('''select crawl_date, status from crawl where spider_id=%s
                     order by crawl_date desc, crawl_time desc limit 1;''', (spider_id,))

    last_crawl = c.fetchone()
    if not last_crawl:
        continue

    spider_data = {'name': spider_name, 'account': account_name}
    crawl_date, status = last_crawl
    if DB == 'sqlite':
        crawl_date = datetime.strptime(crawl_date, '%Y-%m-%d').date()

    if status == 'scheduled':
        if crawl_date < date.today():
            invalid_spiders.append(spider_data)

    elif status == 'running':
        p = subprocess.Popen('ps -ef|grep scrapyd.runner', stdout=subprocess.PIPE, shell=True)
        p.wait()
        output = p.stdout.read()
        if spider_name not in output:
            invalid_spiders.append(spider_data)

if invalid_spiders:
    print 'f'
else:
    print 't'

if len(sys.argv) > 1 and sys.argv[1] == 'verbose':
    print invalid_spiders

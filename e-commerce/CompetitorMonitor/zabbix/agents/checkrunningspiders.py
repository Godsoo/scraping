#!/usr/bin/python

import os
import shutil
import sqlite3
import psycopg2
import sys

DB = 'postgres'


def get_db_connection():
    if DB == 'postgres':
        conn = psycopg2.connect("dbname=productspiders user=productspiders")
    else:
        here = os.path.dirname(os.path.abspath(__file__))

        db_dir = '/home/innodev/product-spiders/productspidersweb/'
        db_filename = 'productspidersweb.db'

        shutil.copy(os.path.join(db_dir, db_filename), here)
        conn = sqlite3.connect(os.path.join(here, db_filename))

    c = conn.cursor()

    return c

def coung_spiders_running_too_long():
    c = get_db_connection()

    if DB == 'sqlite':
        c.execute('''SELECT COUNT(*) FROM crawl WHERE
                     status in ('scheduled', 'running')
                     and crawl_date <= date('now', '-3 day')''')
    else:
        c.execute('''SELECT COUNT(*) FROM crawl WHERE
                     status in ('scheduled', 'running')
                     and crawl_date <= (CURRENT_DATE - INTERVAL '3 day')::date''')

    count = c.fetchone()[0]

    return count


def get_spiders_running_too_long():
    c = get_db_connection()

    if DB == 'sqlite':
        c.execute('''SELECT spider.name FROM spider INNER JOIN crawl ON crawl.spider_id=spider.id
                     WHERE crawl.status in ('scheduled', 'running')
                     AND crawl.crawl_date <= date('now', '-3 day')''')
    else:
        c.execute('''SELECT spider.name FROM spider INNER JOIN crawl ON crawl.spider_id=spider.id
                     WHERE crawl.status in ('scheduled', 'running')
                     AND crawl.crawl_date <= (CURRENT_DATE - INTERVAL '3 day')::date''')
    spiders = c.fetchall()

    return spiders


if __name__ == '__main__':
    task = 'status'
    if len(sys.argv) > 1:
        task = sys.argv[1]

    if task == 'status':
        count = coung_spiders_running_too_long()
        if count:
            print 'f'
        else:
            print 't'
    elif task == 'list':
        spiders = get_spiders_running_too_long()
        for spider in spiders:
            print spider[0]
    else:
        print "Unknown command: '%s'" % task

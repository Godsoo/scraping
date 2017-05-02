#!/usr/bin/python

import psycopg2
import psycopg2.extras
import sys

def get_db_connection():

    conn = psycopg2.connect("dbname=productspiders user=productspiders")
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    return c

def get_spiders_not_running():
    c = get_db_connection()

    # select enabled spiders on enabled accounts
    c.execute('''SELECT spider.name, spider.id FROM spider INNER JOIN account ON spider.account_id=account.id
                 WHERE spider.enabled = true AND account.enabled = true AND spider.crawl_day IS NULL''')

    spiders = c.fetchall()

    invalid_spiders = []
    for spider in spiders:
        c.execute('''SELECT id FROM crawl WHERE spider_id=%s ORDER BY id DESC LIMIT 1''', (spider['id'],))
        crawl = c.fetchone()
        if crawl:
            c.execute('''SELECT COUNT(*) FROM crawl WHERE
                         crawl.id=%s AND
                         status IN ('upload_finished', 'upload_errors', 'crawl_finished')
                         AND crawl_date <= (CURRENT_DATE - INTERVAL '2 day')::date''', (crawl['id'],))
            r = c.fetchone()['count']
            if r:
                invalid_spiders.append(spider)

    return invalid_spiders

if __name__ == '__main__':
    invalid_spiders = get_spiders_not_running()

    task = 'status'
    if len(sys.argv) > 1:
        task = sys.argv[1]

    if task == 'status':
        if invalid_spiders:
            print 'f'
        else:
            print 't'
    elif task == 'list':
        for spider in invalid_spiders:
            print spider['name']
    else:
        print "Unknown command: '%s'" % task

#!/usr/bin/python

import psycopg2

conn = psycopg2.connect("dbname=webalert user=webalert")

cur = conn.cursor()
cur.execute("SELECT * FROM website_crawl WHERE crawl_status='started' and start_time <= (NOW() - interval '1 day')")

if cur.fetchone():
    print 'f'
else:
    print 't'

#!/usr/bin/python

import psycopg2

conn = psycopg2.connect("dbname=productspiders user=productspiders")

c = conn.cursor()

c.execute('''select count(*) from spider s inner join crawl c on c.spider_id=s.id
                                           left outer join spider_error sp on s.id=sp.spider_id
             where sp.id is null and c.status='errors_found' and now() - c.end_time > interval '24' hour''')

count = c.fetchone()[0]
if count:
    print 'f'
else:
    print 't'

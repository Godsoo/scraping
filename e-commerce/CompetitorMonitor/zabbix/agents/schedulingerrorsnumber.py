#!/usr/bin/python

import psycopg2

conn = psycopg2.connect("dbname=productspiders user=productspiders")

c = conn.cursor()

c.execute("""
select count(*)
from crawl c
join spider s on s.id = c.spider_id
join account a on a.id = s.account_id
where s.enabled
  and a.enabled
  and c.status = 'schedule_errors'
""")

count = c.fetchone()[0]
print count

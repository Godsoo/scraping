#!/usr/bin/python

import psycopg2

conn = psycopg2.connect("dbname=productspiders user=productspiders")

c = conn.cursor()

c.execute("""
select count(*)
from crawl c
join spider s on s.id = c.spider_id
join account a on a.id = s.account_id
left outer join spider_error se on s.id=se.spider_id and se.status <> 'fixed'
where s.enabled
  and a.enabled
  and se.id is null
  and c.status in ('errors_found', 'upload_errors', 'schedule_errors')
""")

count = c.fetchone()[0]
print count

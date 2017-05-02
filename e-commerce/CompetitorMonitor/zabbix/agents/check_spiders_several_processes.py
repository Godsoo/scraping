#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import sys
import psycopg2
import psycopg2.extras
import requests
import requests.exceptions
import pickle
from datetime import datetime, timedelta
import os

here = os.path.abspath(os.path.dirname(__file__))

conn = psycopg2.connect("dbname=productspiders user=productspiders")
c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


main_spiders_server_url = '148.251.79.44'


def get_list_of_jobs(server_url):
    url = server_url + 'listjobs.json?project=default'
    if 'localhost' in url:
        url = url.replace('localhost', main_spiders_server_url)

    r = requests.get(url)

    res = r.json()
    if res['status'] == 'error':
        r = requests.post(url)
        res = r.json()

    if 'running' in res:
        res = res['running']
    elif 'jobs' in res:
        res = res['jobs']
    else:
        print "Error, not found 'running' or 'jobs' in keys of result. Url: %s, method: %s" % (url, r.method)
        return None

    return res


def find_duplicates_processes(worker_server):
    jobs = get_list_of_jobs(worker_server['scrapy_url'])

    spiders_running = set()
    duplicates = set()

    for job in jobs:
        if 'job' in job:
            job = job['job']
        if job['spider'] in spiders_running:
            duplicates.add(job['spider'])

        spiders_running.add(job['spider'])

    return duplicates


def find_duplicate_spider_running_on_one_server():
    res = {}
    c.execute("select * from worker_server")

    for w in c:
        duplicates = find_duplicates_processes(w)

        if duplicates:
            res[w['name']] = duplicates

    return res


if __name__ == '__main__':
    duplicates = find_duplicate_spider_running_on_one_server()

    if duplicates:
        print 'f'
        if len(sys.argv) > 1 and sys.argv[1] == 'verbose':
            for w, spiders in duplicates.items():
                print "Duplicates found on server %s: %s" % (w, ", ".join(spiders))
    else:
        print 't'

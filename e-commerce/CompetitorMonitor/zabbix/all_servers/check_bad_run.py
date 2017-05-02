# -*- coding: utf-8 -*-
"""
This script checks only one thing - if crawl failed but not died.
This is indicated by log file adding only one line after failure:
>> Crawled 0 pages (at 0 pages/min), scraped 0 items (at 0 items/min)

Scrapy adds one such line to log file every minute.

To make sure it's really a failure script checks that last 10 lines in log file are only this kind of line.
"""
import os.path
import subprocess
import datetime as dt
import re
from argparse import ArgumentParser

import psycopg2
import psycopg2.extras
import scrapy
import dateutil.parser

# setting log dir
here = os.path.abspath(os.path.dirname(__file__))
root = os.path.dirname(os.path.dirname(here))
if scrapy.version_info > (1, 0, 0):
    log_dir = 'logs/default/'
else:
    log_dir = '.scrapy/scrapyd/logs/default'
log_dir = os.path.join(root, log_dir)
# change to proper host
DB_CONN_STR = "host=148.251.79.44 dbname=productspiders user=productspiders password=productspiders"
# change to proper id of worker server
server_id = None
bad_line_reg = re.compile(r'Crawled \d+ pages \(at 0 pages/min\), scraped \d+ items \(at 0 items/min\)', re.I)
bsm_idle_log = 'DEBUG: [BSM] Spider idle'
scraped_products_count_reg = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Crawled \d+ pages \(at \d* pages/min\)'
                                        r', scraped (\d+) items \(at \d* items/min\)', re.I)
timestamp_threshold = dt.timedelta(hours=3)
number_of_products_unchanged_timestamp_threshold = dt.timedelta(hours=6)


def get_file_last_lines(filepath, lines_num=10000):
    try:
        output = subprocess.check_output(['tail', '-n', str(lines_num), filepath])
    except subprocess.CalledProcessError, e:
        print "Error getting last lines from file %s: %s" % (filepath, str(e))
        return None
    else:
        return output.splitlines()


def get_last_timestamp(lines):
    for line in reversed(lines):
        if len(line) < 19:
            continue
        try:
            res = dateutil.parser.parse(line[:19])
        except (ValueError, TypeError):
            pass
        else:
            return res
    return None


def check_number_of_products_does_not_change(output):
    now = dt.datetime.now()
    most_recent_scraped_dt = None
    most_recent_scraped_count = None
    prev_scraped_dt = None
    prev_scraped_count = None
    for line in output:
        m = scraped_products_count_reg.search(line)
        if m:
            temp_dt = dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
            temp_count = int(m.group(2))
            if temp_dt > now - number_of_products_unchanged_timestamp_threshold:
                # this log is from last 6 hours of crawling
                if most_recent_scraped_dt is None:
                    most_recent_scraped_dt = temp_dt
                    most_recent_scraped_count = temp_count
                # if number of products is not equal previously found number of products in last 6 hours
                # then it's OK
                if temp_count != most_recent_scraped_count:
                    return False
            else:
                # this log is from before last 6 hours of crawling
                # we need to collect latest log
                if prev_scraped_dt is None or temp_dt > prev_scraped_dt:
                    prev_scraped_dt = temp_dt
                    prev_scraped_count = temp_count
    if prev_scraped_dt and most_recent_scraped_dt:
        if prev_scraped_count == most_recent_scraped_count:
            return True
    return False


def check_logs_are_bad(output):
    stuck_crawl = all([bad_line_reg.search(line) for line in output[-20:]])
    stuck_bsm_crawl = sum([bsm_idle_log in line for line in output]) > 1
    not_collecting_products = check_number_of_products_does_not_change(output)
    return stuck_crawl or stuck_bsm_crawl or not_collecting_products


def bad_run(spider_name, jobid):
    filename = '%s.log' % jobid
    filepath = os.path.join(log_dir, spider_name, filename)
    if not os.path.exists(filepath):
        # file not exists
        return True
    else:
        output = get_file_last_lines(filepath)
        last_timestamp = get_last_timestamp(output)
        # return True if 20 last lines lines are "crawled 0 pages..."
        logs_are_bad = check_logs_are_bad(output)
        timestamp_is_bad = (last_timestamp is not None) and (last_timestamp + timestamp_threshold < dt.datetime.now())
        return logs_are_bad and timestamp_is_bad


def get_errors(server_id):
    conn = psycopg2.connect(DB_CONN_STR)
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    spider_errors = []
    c.execute("select * from crawl where worker_server_id=%s and status='running'", (server_id, ))
    for crawl in c.fetchall():
        c.execute("select name from spider where id=%s", (crawl['spider_id'], ))
        spider_name = c.fetchone()['name']
        if bad_run(spider_name, crawl['jobid']):
            spider_errors.append(crawl['spider_id'])

    errors = []
    for spider_id in spider_errors:
        c.execute("select name from spider where id=%s", (spider_id, ))
        errors.append(c.fetchone()['name'])
    return errors


def main(server_id):
    parser = ArgumentParser(description='Checks if running spiders has issues, indicated by log files')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--output-file', dest='output_file', default=None)

    args = parser.parse_args()

    errors = get_errors(server_id)

    if args.output_file:
        with open(args.output_file, 'w+') as f:
            if args.verbose:
                for spider_name in errors:
                    f.write(spider_name)
                    f.write('\n')
            else:
                if len(errors):
                    f.write('f')
                else:
                    f.write('t')
    if args.verbose:
        for spider_name in errors:
            print spider_name
    else:
        if len(errors):
            print 'f'
        else:
            print 't'


if __name__ == '__main__':
    main(server_id)

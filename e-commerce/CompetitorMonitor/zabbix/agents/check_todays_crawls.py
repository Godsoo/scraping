#!/usr/bin/python
# -*- coding: utf-8 -*-
from datetime import date

from psql_conn import c

minimum_number_of_crawls = 200


def check_todays_crawls_error():
    c.execute("select count(*) as number from crawl where crawl_date='%s';" % str(date.today()))
    res = c.fetchone()
    res = res['number']

    if res < minimum_number_of_crawls:
        return True
    else:
        return False


if __name__ == '__main__':
    error = check_todays_crawls_error()
    if error:
        print 'f'
    else:
        print 't'

#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys

from check_failed_scheduled_crawls_new import check_failed_spiders_with_status


def check_failed_running_spiders():
    return check_failed_spiders_with_status('running')


if __name__ == '__main__':
    errors, errors_spiders = check_failed_running_spiders()

    task = 'status'
    if len(sys.argv) > 1:
        task = sys.argv[1]

    if task == 'status':
        if errors:
            print 'f'
        else:
            print 't'
    elif task == 'list':
        for spider in errors_spiders:
            print spider
    else:
        print "Unknown command: '%s'" % task
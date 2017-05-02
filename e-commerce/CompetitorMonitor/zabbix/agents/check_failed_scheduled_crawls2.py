#!/usr/bin/python
# -*- coding: utf-8 -*-
import os

from check_failed_scheduled_crawls import check_failed_scheduled_spiders
from check_failed_scheduled_crawls_new import check_failed_scheduled_spiders as check_failed_scheduled_spiders_new

here = os.path.abspath(os.path.dirname(__file__))


if __name__ == '__main__':
    errors, errors_spiders = check_failed_scheduled_spiders()
    errors2, errors_spiders2 = check_failed_scheduled_spiders_new()
    errors = errors or errors2
    errors_spiders = errors_spiders + errors_spiders2

    for e in errors_spiders:
        print e

    f = open('/tmp/failed_scheduled', 'w')
    for e in set(errors_spiders):
        f.write(e + '\n')
    f.close()
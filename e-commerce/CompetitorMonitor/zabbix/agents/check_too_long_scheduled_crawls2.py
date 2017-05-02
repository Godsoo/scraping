#!/usr/bin/python
# -*- coding: utf-8 -*-
import os

from check_too_long_scheduled_crawls import check_too_long_scheduled_spiders

here = os.path.abspath(os.path.dirname(__file__))


if __name__ == '__main__':
    errors, errors_spiders = check_too_long_scheduled_spiders()
    for e in errors_spiders:
        print e

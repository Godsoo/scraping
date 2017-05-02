#!/usr/bin/python
# -*- coding: utf-8 -*-
from check_failed_running_crawls import check_failed_running_spiders


if __name__ == '__main__':
    errors, errors_spiders = check_failed_running_spiders()
    for spider in errors_spiders:
        print spider


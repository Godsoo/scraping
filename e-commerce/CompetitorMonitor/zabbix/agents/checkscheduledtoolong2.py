#!/usr/bin/python

from checkscheduledtoolong import get_spiders_scheduled_toolong


if __name__ == '__main__':
    invalid_spiders = get_spiders_scheduled_toolong()
    for spider in invalid_spiders:
        print spider['name']

#!/usr/bin/python
# -*- coding: utf-8 -*-

from checkrunningspiders import get_spiders_running_too_long


if __name__ == '__main__':
    spiders = get_spiders_running_too_long()

    spiders = get_spiders_running_too_long()
    for spider in spiders:
        print spider[0]
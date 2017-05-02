#!/usr/bin/python

from checkspidersnotrunning import get_spiders_not_running


if __name__ == '__main__':
    invalid_spiders = get_spiders_not_running()
    for spider in invalid_spiders:
        print spider['name']

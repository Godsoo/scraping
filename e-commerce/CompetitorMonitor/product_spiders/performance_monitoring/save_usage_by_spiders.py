# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import datetime

from get_list_of_working_spiders import get_spiders_usage

from product_spiders.db import Session
from productspidersweb.models import SpiderResourcesUsage


def main():
    db_session = Session()

    spider_usage = get_spiders_usage()

    now = datetime.datetime.now()

    for data in spider_usage:
        spider = data['spider']
        cpu_usage = data['cpu_usage']
        mem_usage = data['mem_usage']

        usage = SpiderResourcesUsage()
        usage.spider_id = spider.id
        usage.worker_server_id = spider.worker_server_id
        usage.time = now
        usage.cpu_usage = cpu_usage
        usage.mem_usage = mem_usage

        db_session.add(usage)

    db_session.commit()
    db_session.close()


if __name__ == '__main__':
    main()
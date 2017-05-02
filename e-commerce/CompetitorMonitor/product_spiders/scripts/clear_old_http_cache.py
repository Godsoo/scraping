# -*- coding: utf-8 -*-
import sys
import os
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))

sys.path.append(os.path.abspath(os.path.join(HERE, '..')))

from db import CacheSession


def main():
    db_session = CacheSession()

    threshold = date.today() - timedelta(days=2)
    threshold = threshold.strftime('%Y-%m-%d')

    db_session.execute("DELETE FROM http_cache_binary WHERE ts < '%s'" % threshold)
    db_session.commit()


if __name__ == '__main__':
    main()
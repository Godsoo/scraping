from datetime import datetime
from datetime import date
from time import mktime
from pytz import timezone


def gmt_datetime(gmt_time):
    return datetime.fromtimestamp(mktime(gmt_time))


def gmt_date(gmt_date_):
    return date.fromtimestamp(mktime(gmt_date_))


def timezone_datetime(gmt_time, tz='Europe/London'):
    if tz == 'GMT':
        return gmt_datetime(gmt_time)
    gmt = datetime.fromtimestamp(mktime(gmt_time))
    gmt_tz = timezone('GMT')
    local_tz = timezone(tz)
    gmt_dt = gmt_tz.localize(gmt)
    return gmt_dt.astimezone(local_tz)


def timezone_date(gmt_date_, tz='Europe/London'):
    if tz == 'GMT':
        return gmt_date(gmt_date_)
    t = timezone_datetime(gmt_date_, tz)
    return date(year=t.year, month=t.month, day=t.day)

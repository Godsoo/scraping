#!/usr/bin/python

import urllib2
import json
from datetime import datetime
from datetime import timedelta
import sys

REPORTS = {
#	 'sagemcom': {'hour': 10, 'minute': 0},
#        'bosch_py': {'hour': 10, 'minute': 0},
        'american_rv': {'hour': 15, 'minute': 49, 'day': 1},
        'bookingisrael': {'hour': 10, 'minute': 0},
#        'bosch': {'hour': 5, 'minute': 0},
#        'bosch_german': {'hour': 5, 'minute': 0}
}

current_time = urllib2.urlopen('http://competitormonitor.com/time.php').read().strip()
current_time = datetime.strptime(current_time, '%Y-%m-%d %H:%M')


last_sent_data = urllib2.urlopen('http://competitormonitor.com/last_sent').read()
last_sent_data = json.loads(last_sent_data)

res = True
errors = []

for report in REPORTS:
    day = REPORTS[report].get('day')
    if last_sent_data.get(report) and (day is None or current_time.weekday() == day):
        expected_time = datetime(year=current_time.year, month=current_time.month, day=current_time.day,
                                 hour=REPORTS[report]['hour'], minute=REPORTS[report]['minute'])
        last_sent = datetime.strptime(last_sent_data[report], '%Y-%m-%d %H:%M')

        if current_time >= expected_time + timedelta(minutes=30) and last_sent.day != current_time.day:
            errors.append(report)
            res = False
    if not report in last_sent_data:
        errors.append(report)
        res = False

if res:
    print 't'
else:
    print 'f'


if len(sys.argv) > 1 and sys.argv[1] == 'verbose':
    for report in errors:
        print report

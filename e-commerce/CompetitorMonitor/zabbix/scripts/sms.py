#!/usr/bin/python

import urllib2
from urllib import urlencode
import sys

user = ''
passwd = ''
api_id = ''
to = sys.argv[1]
subject = sys.argv[2]
message = sys.argv[3]

url = 'http://api.clickatell.com/http/sendmsg?' + urlencode({'user': user, 'password': passwd, 'api_id': api_id,
                                                             'to': to, 'text': subject})
print urllib2.urlopen(url).read()


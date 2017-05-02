#!/usr/bin/python

import smtplib

user = 'competitormonitornotifier@gmail.com'
passwd = 'competitor4'

try:
    mailServer = smtplib.SMTP('smtp.gmail.com', 587)
    mailServer.ehlo()
    mailServer.starttls()
    mailServer.ehlo()
    mailServer.login(user, passwd)
    print 't'
except Exception:
    print 'f'

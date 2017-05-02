#!/usr/bin/python

import smtplib
import sys

from email.mime.text import MIMEText

msg = MIMEText(sys.argv[3])
me = 'spiders@competitormonitor.com'
msg['Subject'] = sys.argv[2]
msg['From'] = me
msg['To'] = sys.argv[1]

s = smtplib.SMTP('mail.competitormonitor.com')
s.login(me, 'f0iZCcM0')
s.sendmail(me, [sys.argv[1]], msg.as_string())
s.quit()

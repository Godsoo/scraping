#!/usr/bin/python
import socket

try:
    socket.create_connection(('competitormonitor.com', 2777))
    print "t"
except Exception:
    print "f"


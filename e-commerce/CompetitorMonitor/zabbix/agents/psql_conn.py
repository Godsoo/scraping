# -*- coding: utf-8 -*-
import psycopg2
import psycopg2.extras

conn = psycopg2.connect("host=localhost dbname=productspiders user=productspiders")
c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
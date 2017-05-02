import sys
import os
import ConfigParser

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

HERE = os.path.dirname(os.path.abspath(__file__))

db_path =  os.path.join(HERE, '../productspidersweb/productspidersweb.db')
db_path = os.path.abspath(db_path)


#DB_URI = 'sqlite:///%s' % db_path


DB_URI = 'postgresql://productspiders:productspiders@localhost:5432/productspiders'

here = os.path.dirname(os.path.abspath(__file__))
fname = os.path.join(here, 'config.ini')
if os.path.exists(fname):
    config = ConfigParser.RawConfigParser()
    config.read(fname)
    if config.has_section('postgres'):
        DB_URI = config.get('postgres', 'uri')

engine = create_engine(DB_URI, poolclass=NullPool, connect_args={'connect_timeout': 120})
Session = sessionmaker(bind=engine)

CACHE_DB_URI = 'postgresql://productspiders:productspiders@localhost:5432/spiders_http_cache'
cache_engine = create_engine(CACHE_DB_URI, poolclass=NullPool, connect_args={'connect_timeout': 120})
CacheSession = sessionmaker(bind=cache_engine)

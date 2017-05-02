from sqlalchemy.orm import joinedload

from product_spiders.db import *
from productspidersweb.models import Spider

__author__ = 'juraseg'

engine_ = create_engine(DB_URI, poolclass=NullPool, connect_args={'connect_timeout': 120})
Session_ = sessionmaker(bind=engine_)

def load_spiders_db_data():
    """
    Load all spiders db records
    :return: list of spider db models
    """
    db_session = Session_()
    res = db_session.query(Spider).all()
    db_session.close()
    return res


def load_spider_db_data(spider_name, load_joined=None):
    """
    Load spider db data by spider name
    :param spider_name: spider name
    :return: spider db model
    """
    db_session = Session_()
    if load_joined is None:
        load_joined = []
    db_spider = db_session.query(Spider).filter(Spider.name == spider_name)
    for column_name in load_joined:
        db_spider = db_spider.options(joinedload(getattr(Spider, column_name)))
    db_spider = db_spider.first()
    db_session.close()
    return db_spider
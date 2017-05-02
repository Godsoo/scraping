import transaction

__author__ = 'juraseg'

def _initTestingDB():
    from sqlalchemy import create_engine
    from productspidersweb.models import (
        DBSession,
        Base
        )
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    DBSession.configure(bind=engine)
    with transaction.manager:
        pass
    return DBSession
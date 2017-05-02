# -*- coding: utf-8 -*-
import os.path

import transaction
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from productspidersweb.models import (
    DBSession,

    Account,
    UploadDestination
)

def migrate_upload_destinations(db_session):
    old_system_dst = db_session.query(UploadDestination).filter(UploadDestination.name == 'old_system').first()
    new_system_dst = db_session.query(UploadDestination).filter(UploadDestination.name == 'new_system').first()
    keter_system_dst = db_session.query(UploadDestination).filter(UploadDestination.name == 'keter_system').first()
    for account in db_session.query(Account).all():
        old_system = False
        new_system = False
        keter_system = False
        # determine upload types
        if account.upload_new_and_old:
            old_system = True
            new_system = True
        else:
            if account.upload_new_system:
                new_system = True
            elif account.upload_keter_system:
                keter_system = True
            else:
                old_system = True

        if old_system:
            if not old_system_dst in account.upload_destinations:
                account.upload_destinations.append(old_system_dst)
        if new_system:
            if not new_system_dst in account.upload_destinations:
                account.upload_destinations.append(new_system_dst)
        if keter_system:
            if not keter_system_dst in account.upload_destinations:
                account.upload_destinations.append(keter_system_dst)

    db_session.commit()


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    db_uri = 'sqlite:///%(root)s/productspidersweb/productspidersweb.db' % {'root': root}
    engine = create_engine(db_uri)
    db_session = sessionmaker(bind=engine)()

    migrate_upload_destinations(db_session)
